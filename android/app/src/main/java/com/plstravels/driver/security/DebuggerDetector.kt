package com.plstravels.driver.security

import android.os.Debug
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Detects debugging attempts and development tools
 */
@Singleton
class DebuggerDetector @Inject constructor() {
    
    /**
     * Comprehensive debugger detection
     */
    fun isDebuggerDetected(): DebuggerResult {
        val detections = mutableListOf<DebuggerDetection>()
        
        // Android Debug API detection
        if (Debug.isDebuggerConnected()) {
            detections.add(DebuggerDetection.DEBUGGER_CONNECTED)
        }
        
        if (Debug.waitingForDebugger()) {
            detections.add(DebuggerDetection.WAITING_FOR_DEBUGGER)
        }
        
        // Native debugger detection
        if (isGdbAttached()) {
            detections.add(DebuggerDetection.GDB_ATTACHED)
        }
        
        if (isStracingDetected()) {
            detections.add(DebuggerDetection.STRACE_DETECTED)
        }
        
        // Check for debugging processes
        if (areDebugProcessesRunning()) {
            detections.add(DebuggerDetection.DEBUG_PROCESSES)
        }
        
        // Check for reverse engineering tools
        if (areReverseEngineeringToolsDetected()) {
            detections.add(DebuggerDetection.REVERSE_ENGINEERING_TOOLS)
        }
        
        return DebuggerResult(
            isDetected = detections.isNotEmpty(),
            detections = detections
        )
    }
    
    /**
     * Detects if GDB is attached to the process
     */
    private fun isGdbAttached(): Boolean {
        return try {
            val statusFile = File("/proc/self/status")
            if (statusFile.exists()) {
                val content = statusFile.readText()
                val tracerPidLine = content.lines().find { it.startsWith("TracerPid:") }
                if (tracerPidLine != null) {
                    val tracerPid = tracerPidLine.split("\t")[1].toIntOrNull() ?: 0
                    tracerPid != 0
                } else {
                    false
                }
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Detects strace or other tracing tools
     */
    private fun isStracingDetected(): Boolean {
        return try {
            // Check if process is being traced
            val statFile = File("/proc/self/stat")
            if (statFile.exists()) {
                val content = statFile.readText()
                val fields = content.split(" ")
                if (fields.size > 6) {
                    val flags = fields[8].toLongOrNull() ?: 0
                    // Check PF_TRACESYS flag (0x00000020)
                    (flags and 0x00000020) != 0L
                } else {
                    false
                }
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Checks for running debug processes
     */
    private fun areDebugProcessesRunning(): Boolean {
        val debugProcesses = listOf(
            "gdb", "gdbserver", "lldb", "strace", "ltrace",
            "objdump", "readelf", "nm", "strings", "hexdump"
        )
        
        return try {
            val process = Runtime.getRuntime().exec("ps")
            val output = process.inputStream.bufferedReader().readText()
            debugProcesses.any { debugProcess ->
                output.contains(debugProcess)
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Detects reverse engineering tools and frameworks
     */
    private fun areReverseEngineeringToolsDetected(): Boolean {
        val reverseEngineeringTools = listOf(
            // Frida
            "frida-server", "frida-agent", "frida-gadget",
            // Xposed
            "xposed", "XposedBridge",
            // Other tools
            "substrate", "cydia", "ssl-kill-switch",
            // IDA Pro mobile debugger
            "android_server", "ida_android_server"
        )
        
        return reverseEngineeringTools.any { tool ->
            isProcessRunning(tool) || isLibraryLoaded(tool)
        }
    }
    
    /**
     * Checks if a specific process is running
     */
    private fun isProcessRunning(processName: String): Boolean {
        return try {
            val process = Runtime.getRuntime().exec("ps | grep $processName")
            val output = process.inputStream.bufferedReader().readText()
            output.isNotEmpty() && !output.contains("grep")
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Checks if a library is loaded in the current process
     */
    private fun isLibraryLoaded(libraryName: String): Boolean {
        return try {
            val mapsFile = File("/proc/self/maps")
            if (mapsFile.exists()) {
                val content = mapsFile.readText()
                content.contains(libraryName)
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Anti-debugging using timing attacks
     */
    fun performTimingCheck(): Boolean {
        val startTime = System.nanoTime()
        
        // Perform some operations that would be slower under debugging
        var dummy = 0
        for (i in 0..1000) {
            dummy += i * i
        }
        
        val endTime = System.nanoTime()
        val duration = endTime - startTime
        
        // If operation took significantly longer than expected, debugger might be attached
        return duration > 10_000_000 // 10ms threshold
    }
    
    /**
     * Checks for debugging-related environment variables
     */
    fun checkDebugEnvironment(): Boolean {
        val debugEnvVars = listOf(
            "ANDROID_DEBUG", "DEBUG", "DEBUGGING",
            "FRIDA_AGENT_PATH", "FRIDA_SCRIPT_PATH"
        )
        
        return debugEnvVars.any { envVar ->
            System.getenv(envVar) != null
        }
    }
}

/**
 * Result of debugger detection
 */
data class DebuggerResult(
    val isDetected: Boolean,
    val detections: List<DebuggerDetection>
)

/**
 * Types of debugger detections
 */
enum class DebuggerDetection {
    DEBUGGER_CONNECTED,
    WAITING_FOR_DEBUGGER,
    GDB_ATTACHED,
    STRACE_DETECTED,
    DEBUG_PROCESSES,
    REVERSE_ENGINEERING_TOOLS
}