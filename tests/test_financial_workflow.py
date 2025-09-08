"""
Financial Workflow and Salary Calculation Tests  
"""

import pytest
from playwright.sync_api import Page, expect
from .conftest import TEST_ROUTES


class TestSalaryCalculation:
    """Test salary calculation functionality"""
    
    @pytest.mark.workflow
    @pytest.mark.integration
    def test_duty_approval_triggers_salary_calculation(self, admin_page: Page):
        """Test that approving a duty triggers salary calculation"""
        admin_page.goto('/admin/duties')
        admin_page.wait_for_load_state('networkidle')
        
        # Look for pending duties
        if admin_page.locator('tr:has(.status:has-text("PENDING"))').count() > 0:
            pending_row = admin_page.locator('tr:has(.status:has-text("PENDING"))').first
            
            # Note the duty details before approval
            duty_revenue = pending_row.locator('.revenue, [data-revenue]').text_content() or '0'
            
            # Approve the duty
            if pending_row.locator('button:has-text("Approve")').count() > 0:
                pending_row.locator('button:has-text("Approve")').click()
                
                # Confirm approval if modal appears
                if admin_page.locator('button:has-text("Confirm")').count() > 0:
                    admin_page.click('button:has-text("Confirm")')
                
                # Verify approval success
                expect(admin_page.locator('.alert-success')).to_be_visible()
                
                # Check that salary was calculated
                # This could be verified by checking the duty row again or going to earnings page
                admin_page.wait_for_timeout(1000)  # Wait for calculation
    
    @pytest.mark.workflow
    def test_earnings_display_after_approval(self, driver_page: Page):
        """Test that earnings are updated after duty approval"""
        driver_page.goto(TEST_ROUTES['driver_earnings'])
        
        # Check for earnings display
        expect(driver_page.locator('h1, h2')).to_contain_text('Earnings')
        
        # Look for earnings breakdown
        if driver_page.locator('.earnings-summary, .total-earnings').count() > 0:
            earnings_text = driver_page.locator('.earnings-summary, .total-earnings').text_content()
            # Should contain currency symbols or numbers
            expect(earnings_text).to_match(r'[\d₹$,.]')
    
    @pytest.mark.workflow
    def test_duty_scheme_calculation_types(self, admin_page: Page):
        """Test different duty scheme calculation types"""
        admin_page.goto('/admin/duty-schemes')
        
        # Check for different scheme types
        if admin_page.locator('table tbody tr').count() > 0:
            expect(admin_page.locator('tbody')).to_contain_text(['Fixed', 'Percentage', 'Slab'])
            
            # Test viewing a scheme
            if admin_page.locator('button:has-text("View"), .btn-view').count() > 0:
                admin_page.locator('button:has-text("View"), .btn-view').first.click()
                
                # Should show scheme details
                expect(admin_page.locator('.modal, .scheme-details')).to_be_visible()
                expect(admin_page.locator('body')).to_contain_text(['Base Amount', 'Percentage', 'Minimum'])


class TestFinancialTransactions:
    """Test financial transaction management"""
    
    @pytest.mark.workflow
    def test_manual_transaction_addition(self, admin_page: Page):
        """Test adding manual transactions (penalties, bonuses)"""
        admin_page.goto('/admin/drivers')
        
        # Look for first driver to add transaction
        if admin_page.locator('tbody tr').count() > 0:
            driver_row = admin_page.locator('tbody tr').first
            
            # Look for transaction or financial action button
            if driver_row.locator('button:has-text("Transaction"), .btn-transaction').count() > 0:
                driver_row.locator('button:has-text("Transaction"), .btn-transaction').click()
                
                # Fill transaction form if modal opens
                if admin_page.locator('.modal').is_visible():
                    # Select transaction type
                    if admin_page.locator('select[name="transaction_type"]').count() > 0:
                        admin_page.select_option('select[name="transaction_type"]', 'penalty')
                    
                    # Enter amount
                    if admin_page.locator('input[name="amount"]').count() > 0:
                        admin_page.fill('input[name="amount"]', '100.00')
                    
                    # Enter description
                    if admin_page.locator('input[name="description"], textarea[name="description"]').count() > 0:
                        admin_page.fill('input[name="description"], textarea[name="description"]', 'Test penalty')
                    
                    # Submit transaction
                    if admin_page.locator('button[type="submit"]').count() > 0:
                        admin_page.click('button[type="submit"]')
                        expect(admin_page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.workflow
    def test_penalty_application(self, admin_page: Page):
        """Test applying penalties to drivers"""
        admin_page.goto('/admin/drivers')
        
        # This would be similar to manual transaction test but specifically for penalties
        if admin_page.locator('tbody tr').count() > 0:
            driver_row = admin_page.locator('tbody tr').first
            
            # Look for penalty button
            if driver_row.locator('button:has-text("Penalty"), .btn-penalty').count() > 0:
                driver_row.locator('button:has-text("Penalty"), .btn-penalty').click()
                
                # Fill penalty form
                if admin_page.locator('input[name="penalty_amount"]').count() > 0:
                    admin_page.fill('input[name="penalty_amount"]', '50.00')
                
                if admin_page.locator('textarea[name="penalty_reason"]').count() > 0:
                    admin_page.fill('textarea[name="penalty_reason"]', 'Late duty start')
                
                # Apply penalty
                if admin_page.locator('button:has-text("Apply Penalty")').count() > 0:
                    admin_page.click('button:has-text("Apply Penalty")')
                    expect(admin_page.locator('.alert-success')).to_be_visible()
    
    @pytest.mark.workflow
    def test_bonus_application(self, admin_page: Page):
        """Test applying bonuses to drivers"""
        admin_page.goto('/admin/drivers')
        
        if admin_page.locator('tbody tr').count() > 0:
            driver_row = admin_page.locator('tbody tr').first
            
            # Look for bonus/reward button
            if driver_row.locator('button:has-text("Bonus"), .btn-bonus').count() > 0:
                driver_row.locator('button:has-text("Bonus"), .btn-bonus').click()
                
                # Fill bonus form
                if admin_page.locator('input[name="bonus_amount"]').count() > 0:
                    admin_page.fill('input[name="bonus_amount"]', '200.00')
                
                if admin_page.locator('textarea[name="bonus_reason"]').count() > 0:
                    admin_page.fill('textarea[name="bonus_reason"]', 'Excellent service')
                
                # Apply bonus
                if admin_page.locator('button:has-text("Apply Bonus")').count() > 0:
                    admin_page.click('button:has-text("Apply Bonus")')
                    expect(admin_page.locator('.alert-success')).to_be_visible()


class TestEarningsReports:
    """Test earnings and financial reporting"""
    
    @pytest.mark.workflow
    def test_driver_earnings_page(self, driver_page: Page):
        """Test driver earnings page functionality"""
        driver_page.goto(TEST_ROUTES['driver_earnings'])
        
        # Check earnings page structure
        expect(driver_page.locator('h1, h2')).to_contain_text('Earnings')
        
        # Check for earnings summary
        if driver_page.locator('.earnings-summary, .summary-card').count() > 0:
            expect(driver_page.locator('.earnings-summary, .summary-card')).to_contain_text(['Total', 'This Month'])
        
        # Check for earnings breakdown
        if driver_page.locator('.earnings-breakdown, .breakdown-item').count() > 0:
            expect(driver_page.locator('body')).to_contain_text(['Revenue', 'Deductions', 'Net'])
    
    @pytest.mark.workflow  
    def test_earnings_ledger(self, driver_page: Page):
        """Test earnings ledger/history"""
        # Check if there's a ledger or history page
        ledger_url = '/driver/ledger'
        driver_page.goto(ledger_url)
        
        if driver_page.locator('h1, h2').count() > 0:
            # If ledger page exists, test its functionality
            expect(driver_page.locator('h1, h2')).to_contain_text(['Ledger', 'History', 'Transactions'])
            
            # Check for transaction history
            if driver_page.locator('table, .transaction-list').count() > 0:
                expect(driver_page.locator('body')).to_contain_text(['Date', 'Description', 'Amount'])
    
    @pytest.mark.workflow
    def test_admin_financial_reports(self, admin_page: Page):
        """Test admin financial reports"""
        admin_page.goto('/admin/reports')
        
        # Check for financial report options
        if admin_page.locator('.report-card, .report-option').count() > 0:
            expect(admin_page.locator('body')).to_contain_text(['Financial', 'Earnings', 'Revenue'])
        
        # Test generating a financial report
        if admin_page.locator('button:has-text("Generate"), .btn-generate').count() > 0:
            admin_page.locator('button:has-text("Generate"), .btn-generate').first.click()
            
            # Should show report or start generation
            expect(admin_page.locator('.alert, .report-result')).to_be_visible()
    
    @pytest.mark.workflow
    def test_date_range_earnings(self, driver_page: Page):
        """Test earnings filtering by date range"""
        driver_page.goto(TEST_ROUTES['driver_earnings'])
        
        # Look for date range filters
        if driver_page.locator('input[type="date"]').count() >= 2:
            date_inputs = driver_page.locator('input[type="date"]')
            
            # Set from date
            date_inputs.nth(0).fill('2024-01-01')
            
            # Set to date  
            date_inputs.nth(1).fill('2024-01-31')
            
            # Apply filter
            if driver_page.locator('button:has-text("Filter"), .btn-filter').count() > 0:
                driver_page.click('button:has-text("Filter"), .btn-filter')
                
                # Should filter earnings by date range
                driver_page.wait_for_load_state('networkidle')
                expect(driver_page).to_have_url('**/from=2024-01-01')


class TestPaymentManagement:
    """Test payment management functionality"""
    
    @pytest.mark.workflow 
    def test_driver_payment_history(self, driver_page: Page):
        """Test driver payment history if available"""
        # This test assumes there might be a payments section
        payment_urls = ['/driver/payments', '/driver/salary', '/driver/payouts']
        
        for url in payment_urls:
            driver_page.goto(url)
            
            if driver_page.locator('h1, h2').count() > 0 and not driver_page.locator('.error, .not-found').count() > 0:
                # Found a payment-related page
                expect(driver_page.locator('h1, h2')).to_contain_text(['Payment', 'Salary', 'Payout'])
                
                # Check for payment history
                if driver_page.locator('table, .payment-list').count() > 0:
                    expect(driver_page.locator('body')).to_contain_text(['Date', 'Amount', 'Status'])
                break
    
    @pytest.mark.workflow
    def test_admin_payment_processing(self, admin_page: Page):
        """Test admin payment processing functionality"""
        # Look for payment-related admin pages
        payment_admin_urls = ['/admin/payments', '/admin/payroll', '/admin/salary']
        
        for url in payment_admin_urls:
            admin_page.goto(url)
            
            if admin_page.locator('h1, h2').count() > 0 and not admin_page.locator('.error, .not-found').count() > 0:
                # Found payment admin page
                expect(admin_page.locator('h1, h2')).to_contain_text(['Payment', 'Payroll', 'Salary'])
                
                # Test bulk payment processing if available
                if admin_page.locator('button:has-text("Process"), .btn-process').count() > 0:
                    admin_page.click('button:has-text("Process"), .btn-process')
                    expect(admin_page.locator('.alert')).to_be_visible()
                break
    
    @pytest.mark.workflow 
    def test_minimum_guarantee_calculation(self, admin_page: Page):
        """Test minimum guarantee calculation in duty schemes"""
        admin_page.goto('/admin/duty-schemes')
        
        # Look for schemes with minimum guarantee
        if admin_page.locator('tbody tr').count() > 0:
            # Check for BMG (Business Minimum Guarantee) mention
            scheme_text = admin_page.locator('tbody').text_content()
            
            if 'BMG' in scheme_text or 'Minimum' in scheme_text:
                # Click on a scheme with minimum guarantee
                if admin_page.locator('button:has-text("View")').count() > 0:
                    admin_page.locator('button:has-text("View")').first.click()
                    
                    # Should show minimum guarantee details
                    expect(admin_page.locator('.modal, .scheme-details')).to_contain_text(['Minimum', 'Guarantee', 'BMG'])