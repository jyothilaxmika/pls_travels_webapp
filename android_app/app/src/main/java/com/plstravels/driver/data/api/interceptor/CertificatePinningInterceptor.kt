package com.plstravels.driver.data.api.interceptor

import com.plstravels.driver.BuildConfig
import okhttp3.CertificatePinner
import okhttp3.Interceptor
import okhttp3.Response
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton
import javax.net.ssl.SSLPeerUnverifiedException

/**
 * Enhanced certificate pinning interceptor for production security
 */
@Singleton
class CertificatePinningInterceptor @Inject constructor() : Interceptor {
    
    companion object {
        // Production certificate pins for replit.app
        // Note: Replace with actual certificate pins for production deployment
        private val CERTIFICATE_PINNER = CertificatePinner.Builder()
            .add("*.replit.app", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=") // Replace with actual pin
            .add("*.replit.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=") // Replace with actual pin
            .build()
    }
    
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        
        return if (BuildConfig.CERTIFICATE_PINNING_ENABLED && !BuildConfig.DEBUG) {
            try {
                // Validate certificate pins for production builds
                val hostname = request.url.host
                
                // Only pin certificates for our domains
                if (hostname.contains("replit.app") || hostname.contains("replit.com")) {
                    try {
                        CERTIFICATE_PINNER.check(hostname, emptyList())
                    } catch (e: SSLPeerUnverifiedException) {
                        Timber.e(e, "Certificate pinning failed for host: $hostname")
                        throw SecurityException("Certificate pinning validation failed", e)
                    }
                }
                
                val response = chain.proceed(request)
                
                // Additional security headers validation
                validateSecurityHeaders(response)
                
                response
            } catch (e: SecurityException) {
                throw e
            } catch (e: Exception) {
                Timber.e(e, "Certificate pinning error")
                throw SecurityException("Network security validation failed", e)
            }
        } else {
            // Development builds or when pinning is disabled
            if (BuildConfig.DEBUG) {
                Timber.d("Certificate pinning disabled for debug build")
            }
            chain.proceed(request)
        }
    }
    
    /**
     * Validate security headers in response
     */
    private fun validateSecurityHeaders(response: Response) {
        try {
            val requiredHeaders = mapOf(
                "Strict-Transport-Security" to "Expected HSTS header missing",
                "X-Content-Type-Options" to "Expected X-Content-Type-Options header missing",
                "X-Frame-Options" to "Expected X-Frame-Options header missing"
            )
            
            val missingHeaders = mutableListOf<String>()
            
            requiredHeaders.forEach { (header, message) ->
                if (response.header(header) == null) {
                    missingHeaders.add(header)
                    Timber.w(message)
                }
            }
            
            if (missingHeaders.isNotEmpty() && !BuildConfig.DEBUG) {
                Timber.w("Missing security headers: $missingHeaders")
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to validate security headers")
        }
    }
}