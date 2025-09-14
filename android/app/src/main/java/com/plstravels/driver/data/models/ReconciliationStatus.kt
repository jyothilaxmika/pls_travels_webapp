package com.plstravels.driver.data.models

/**
 * Data class representing command reconciliation status
 */
data class ReconciliationStatus(
    val totalCommands: Int,
    val unreconciledCount: Int,
    val needsReconciliation: Boolean
)