"""
Admin routes for driver reminder management
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc

from app import db
from admin_routes import admin_required
from models import (
    DriverReminder, ReminderType, ReminderStatus, Driver, Duty, 
    DutyStatus, DriverStatus, User
)
from services.reminder_service import ReminderService
from services.audit_service import AuditService
from timezone_utils import get_ist_time_naive

admin_reminder_bp = Blueprint('admin_reminder', __name__, url_prefix='/admin/reminders')

reminder_service = ReminderService()
audit_service = AuditService()

@admin_reminder_bp.route('/')
@login_required
@admin_required
def reminders_dashboard():
    """Main reminders dashboard showing overview and statistics"""
    try:
        current_time = get_ist_time_naive()
        
        # Get reminder statistics
        stats = {
            'pending': db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.PENDING.value
            ).count(),
            'sent_today': db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.SENT.value,
                DriverReminder.sent_at >= current_time.replace(hour=0, minute=0, second=0)
            ).count(),
            'failed': db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.FAILED.value
            ).count(),
            'overdue': db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.PENDING.value,
                DriverReminder.scheduled_at < current_time - timedelta(minutes=30)
            ).count()
        }
        
        # Get recent reminders
        recent_reminders = db.session.query(DriverReminder).join(Driver).order_by(
            desc(DriverReminder.created_at)
        ).limit(10).all()
        
        # Get drivers currently needing reminders
        drivers_needing_reminders = reminder_service.identify_drivers_needing_reminders()
        
        return render_template('admin/reminders/dashboard.html',
                             stats=stats,
                             recent_reminders=recent_reminders,
                             drivers_needing_reminders=drivers_needing_reminders)
        
    except Exception as e:
        flash(f'Error loading reminders dashboard: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_reminder_bp.route('/list')
@login_required
@admin_required
def list_reminders():
    """List all reminders with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status_filter = request.args.get('status', '')
        type_filter = request.args.get('type', '')
        driver_search = request.args.get('driver', '')
        channel_filter = request.args.get('channel', '')
        
        # Build query
        query = db.session.query(DriverReminder).join(Driver)
        
        if status_filter:
            query = query.filter(DriverReminder.status == status_filter)
        
        if type_filter:
            query = query.filter(DriverReminder.reminder_type == type_filter)
        
        if driver_search:
            # Handle both ID and text search
            try:
                driver_id = int(driver_search)
                query = query.filter(DriverReminder.driver_id == driver_id)
            except ValueError:
                # Text search on driver name or phone
                query = query.filter(
                    or_(
                        Driver.full_name.ilike(f'%{driver_search}%'),
                        Driver.phone.ilike(f'%{driver_search}%')
                    )
                )
        
        if channel_filter:
            query = query.filter(DriverReminder.channel == channel_filter)
        
        # Order by priority and recency
        query = query.order_by(
            DriverReminder.priority.desc(),
            desc(DriverReminder.created_at)
        )
        
        # Paginate
        reminders = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get filter options
        statuses = [status.value for status in ReminderStatus]
        types = [type_val.value for type_val in ReminderType]
        
        # Get active drivers for filter dropdown
        drivers = db.session.query(Driver).join(User).filter(
            Driver.status == DriverStatus.ACTIVE,
            User.status == UserStatus.ACTIVE
        ).order_by(Driver.full_name).all()

        return render_template('admin/reminders/list.html',
                             reminders=reminders,
                             statuses=statuses,
                             types=types,
                             drivers=drivers,
                             current_filters={
                                 'status': status_filter,
                                 'type': type_filter,
                                 'driver': driver_search,
                                 'channel': channel_filter
                             })
        
    except Exception as e:
        flash(f'Error loading reminders: {str(e)}', 'error')
        return redirect(url_for('admin_reminder.reminders_dashboard'))

@admin_reminder_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_reminder():
    """Create a manual reminder for a driver"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            driver_id = int(data.get('driver_id'))
            reminder_type = data.get('reminder_type')
            message = data.get('message')
            channel = data.get('channel', 'whatsapp')
            priority = data.get('priority', 'normal')
            duty_id = data.get('duty_id')
            
            if not all([driver_id, reminder_type, message]):
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
            # Create reminder
            reminder = reminder_service.create_reminder(
                driver_id=driver_id,
                reminder_type=reminder_type,
                message=message,
                channel=channel,
                duty_id=int(duty_id) if duty_id else None,
                priority=priority,
                context_data={'manual_creation': True, 'created_by_user': current_user.id}
            )
            
            reminder.auto_generated = False
            reminder.created_by = current_user.id
            
            db.session.commit()
            
            # Log the action
            audit_service.log_action(
                action='manual_reminder_created',
                entity_type='driver_reminder',
                entity_id=reminder.id,
                details={
                    'driver_id': driver_id,
                    'reminder_type': reminder_type,
                    'channel': channel
                },
                user_id=current_user.id
            )
            
            if request.is_json:
                return jsonify({'success': True, 'reminder_id': reminder.id})
            else:
                flash(f'Reminder created successfully for driver', 'success')
                return redirect(url_for('admin_reminder.list_reminders'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = f'Error creating reminder: {str(e)}'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 500
            else:
                flash(error_msg, 'error')
                return redirect(url_for('admin_reminder.list_reminders'))
    
    # GET request - show create form
    try:
        # Get active drivers
        from models import UserStatus
        drivers = db.session.query(Driver).join(User).filter(
            Driver.status == DriverStatus.ACTIVE,
            User.status == UserStatus.ACTIVE
        ).order_by(Driver.full_name).all()
        
        # Get active duties for drivers
        active_duties = db.session.query(Duty).filter(
            Duty.status == DutyStatus.ACTIVE
        ).order_by(Duty.actual_start.desc()).all()
        
        reminder_types = [
            (ReminderType.MISSING_START_PHOTO, 'Missing Start Photo'),
            (ReminderType.MISSING_END_PHOTO, 'Missing End Photo'),
            (ReminderType.LONG_ACTIVE_DUTY, 'Long Active Duty'),
            (ReminderType.DUTY_NOT_ENDED, 'Duty Not Ended'),
        ]
        
        return render_template('admin/reminders/create.html',
                             drivers=drivers,
                             active_duties=active_duties,
                             reminder_types=reminder_types)
        
    except Exception as e:
        flash(f'Error loading create reminder form: {str(e)}', 'error')
        return redirect(url_for('admin_reminder.reminders_dashboard'))

@admin_reminder_bp.route('/send/<int:reminder_id>', methods=['POST'])
@login_required
@admin_required
def send_reminder(reminder_id):
    """Manually send a specific reminder"""
    try:
        reminder = db.session.query(DriverReminder).get_or_404(reminder_id)
        
        if reminder.status != ReminderStatus.PENDING:
            return jsonify({'success': False, 'error': 'Reminder is not in pending status'}), 400
        
        success, error_msg = reminder_service.send_reminder(reminder)
        
        if success:
            db.session.commit()
            audit_service.log_action(
                action='manual_reminder_sent',
                entity_type='driver_reminder',
                entity_id=reminder_id,
                user_id=current_user.id
            )
            return jsonify({'success': True, 'message': 'Reminder sent successfully'})
        else:
            db.session.commit()  # Save the failure status
            return jsonify({'success': False, 'error': error_msg}), 500
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error sending reminder: {str(e)}'}), 500

@admin_reminder_bp.route('/resolve/<int:reminder_id>', methods=['POST'])
@login_required
@admin_required
def resolve_reminder(reminder_id):
    """Manually mark a reminder as resolved"""
    try:
        reminder = db.session.query(DriverReminder).get_or_404(reminder_id)
        
        if reminder.status == ReminderStatus.RESOLVED:
            return jsonify({'success': False, 'error': 'Reminder is already resolved'}), 400
        
        reminder.mark_resolved()
        db.session.commit()
        
        audit_service.log_action(
            action='manual_reminder_resolved',
            entity_type='driver_reminder',
            entity_id=reminder_id,
            user_id=current_user.id
        )
        
        return jsonify({'success': True, 'message': 'Reminder marked as resolved'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error resolving reminder: {str(e)}'}), 500

@admin_reminder_bp.route('/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_actions():
    """Perform bulk actions on reminders"""
    try:
        data = request.get_json()
        action = data.get('action')
        reminder_ids = data.get('reminder_ids', [])
        
        if not action or not reminder_ids:
            return jsonify({'success': False, 'error': 'Missing action or reminder IDs'}), 400
        
        reminders = db.session.query(DriverReminder).filter(
            DriverReminder.id.in_(reminder_ids)
        ).all()
        
        if not reminders:
            return jsonify({'success': False, 'error': 'No reminders found'}), 404
        
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for reminder in reminders:
            try:
                if action == 'send' and reminder.status == ReminderStatus.PENDING:
                    success, error_msg = reminder_service.send_reminder(reminder)
                    if success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f'Reminder {reminder.id}: {error_msg}')
                
                elif action == 'resolve' and reminder.status != ReminderStatus.RESOLVED:
                    reminder.mark_resolved()
                    results['success'] += 1
                
                elif action == 'delete':
                    db.session.delete(reminder)
                    results['success'] += 1
                
                else:
                    results['failed'] += 1
                    results['errors'].append(f'Reminder {reminder.id}: Invalid action or status')
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f'Reminder {reminder.id}: {str(e)}')
        
        db.session.commit()
        
        audit_service.log_action(
            action=f'bulk_reminder_{action}',
            entity_type='driver_reminder',
            entity_id=None,
            details={
                'reminder_ids': reminder_ids,
                'results': results
            },
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'Bulk action completed: {results["success"]} successful, {results["failed"]} failed'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error performing bulk action: {str(e)}'}), 500

@admin_reminder_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """Show reminder analytics and trends"""
    try:
        current_time = get_ist_time_naive()
        week_ago = current_time - timedelta(days=7)
        month_ago = current_time - timedelta(days=30)
        
        # Weekly trends
        weekly_stats = {
            'sent': db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.SENT,
                DriverReminder.sent_at >= week_ago
            ).count(),
            'resolved': db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.RESOLVED,
                DriverReminder.resolved_at >= week_ago
            ).count(),
            'failed': db.session.query(DriverReminder).filter(
                DriverReminder.status == ReminderStatus.FAILED,
                DriverReminder.updated_at >= week_ago
            ).count()
        }
        
        # Reminder type breakdown
        type_breakdown = db.session.query(
            DriverReminder.reminder_type,
            func.count(DriverReminder.id).label('count')
        ).filter(
            DriverReminder.created_at >= month_ago
        ).group_by(DriverReminder.reminder_type).all()
        
        # Channel effectiveness
        channel_stats = db.session.query(
            DriverReminder.channel,
            DriverReminder.status,
            func.count(DriverReminder.id).label('count')
        ).filter(
            DriverReminder.created_at >= month_ago
        ).group_by(DriverReminder.channel, DriverReminder.status).all()
        
        # Top drivers needing reminders
        top_drivers = db.session.query(
            Driver,
            func.count(DriverReminder.id).label('reminder_count')
        ).join(DriverReminder).filter(
            DriverReminder.created_at >= month_ago
        ).group_by(Driver.id).order_by(
            desc(func.count(DriverReminder.id))
        ).limit(10).all()
        
        return render_template('admin/reminders/analytics.html',
                             weekly_stats=weekly_stats,
                             type_breakdown=type_breakdown,
                             channel_stats=channel_stats,
                             top_drivers=top_drivers)
        
    except Exception as e:
        flash(f'Error loading analytics: {str(e)}', 'error')
        return redirect(url_for('admin_reminder.reminders_dashboard'))

@admin_reminder_bp.route('/api/process-pending', methods=['POST'])
@login_required
@admin_required
def api_process_pending():
    """API endpoint to manually trigger processing of pending reminders"""
    try:
        stats = reminder_service.process_pending_reminders()
        
        audit_service.log_action(
            action='manual_reminder_processing',
            entity_type='system',
            entity_id=None,
            details=stats,
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'stats': stats,
            'message': f'Processed {stats["processed"]} reminders: {stats["sent"]} sent, {stats["failed"]} failed'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error processing reminders: {str(e)}'}), 500

@admin_reminder_bp.route('/api/generate-reminders', methods=['POST'])
@login_required
@admin_required
def api_generate_reminders():
    """API endpoint to manually generate reminders for identified issues"""
    try:
        stats = reminder_service.create_reminders_for_identified_issues()
        
        audit_service.log_action(
            action='manual_reminder_generation',
            entity_type='system',
            entity_id=None,
            details=stats,
            user_id=current_user.id
        )
        
        total_created = sum(stats.values())
        return jsonify({
            'success': True,
            'stats': stats,
            'message': f'Created {total_created} new reminders'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error generating reminders: {str(e)}'}), 500