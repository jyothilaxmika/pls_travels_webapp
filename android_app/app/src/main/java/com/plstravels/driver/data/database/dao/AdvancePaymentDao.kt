package com.plstravels.driver.data.database.dao

import androidx.room.*
import com.plstravels.driver.data.database.entity.AdvancePaymentEntity

/**
 * Room DAO for advance payment operations
 */
@Dao
interface AdvancePaymentDao {
    
    @Query("SELECT * FROM advance_payments WHERE id = :paymentId")
    suspend fun getAdvancePaymentById(paymentId: String): AdvancePaymentEntity?
    
    @Query("SELECT * FROM advance_payments WHERE dutyId = :dutyId")
    suspend fun getAdvancePaymentsByDutyId(dutyId: Int): List<AdvancePaymentEntity>
    
    @Query("SELECT * FROM advance_payments WHERE status = :status")
    suspend fun getAdvancePaymentsByStatus(status: String): List<AdvancePaymentEntity>
    
    @Query("SELECT * FROM advance_payments WHERE isSynced = 0")
    suspend fun getUnsyncedAdvancePayments(): List<AdvancePaymentEntity>
    
    @Query("SELECT * FROM advance_payments ORDER BY createdAt DESC")
    suspend fun getAllAdvancePayments(): List<AdvancePaymentEntity>
    
    @Query("SELECT * FROM advance_payments WHERE status = 'PENDING' ORDER BY createdAt DESC")
    suspend fun getPendingAdvancePayments(): List<AdvancePaymentEntity>
    
    @Query("SELECT * FROM advance_payments WHERE status = 'APPROVED' ORDER BY createdAt DESC")
    suspend fun getApprovedAdvancePayments(): List<AdvancePaymentEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAdvancePayment(payment: AdvancePaymentEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAdvancePayments(payments: List<AdvancePaymentEntity>)
    
    @Update
    suspend fun updateAdvancePayment(payment: AdvancePaymentEntity)
    
    @Delete
    suspend fun deleteAdvancePayment(payment: AdvancePaymentEntity)
    
    @Query("DELETE FROM advance_payments WHERE id = :paymentId")
    suspend fun deleteAdvancePaymentById(paymentId: String)
    
    @Query("UPDATE advance_payments SET status = :status, amountApproved = :amountApproved, respondedAt = :respondedAt, responseNotes = :responseNotes WHERE id = :paymentId")
    suspend fun updatePaymentResponse(paymentId: String, status: String, amountApproved: Double?, respondedAt: Long, responseNotes: String?)
    
    @Query("UPDATE advance_payments SET isSynced = :isSynced WHERE id = :paymentId")
    suspend fun updateSyncStatus(paymentId: String, isSynced: Boolean)
}