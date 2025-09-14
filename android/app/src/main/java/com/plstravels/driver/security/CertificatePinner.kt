package com.plstravels.driver.security

import okhttp3.CertificatePinner
import okhttp3.OkHttpClient
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Certificate pinning configuration for secure network communications
 */
@Singleton
class CertificatePinnerConfig @Inject constructor() {
    
    /**
     * Creates a certificate pinner with production and staging pins
     */
    fun createCertificatePinner(): CertificatePinner {
        return CertificatePinner.Builder()
            // Production API pins (replace with your actual certificate hashes)
            .add("api.plstravels.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
            .add("api.plstravels.com", "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=")
            
            // Staging API pins
            .add("staging-api.plstravels.com", "sha256/CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=")
            .add("staging-api.plstravels.com", "sha256/DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD=")
            
            // Firebase/Google Services pins
            .add("firebase.googleapis.com", "sha256/WoiWRyIOVNa9ihaBciRSC7XHjliYS9VwUGOIud4PB18=")
            .add("*.googleapis.com", "sha256/WoiWRyIOVNa9ihaBciRSC7XHjliYS9VwUGOIud4PB18=")
            .add("*.googleapis.com", "sha256/JSMzqOOrtyOT1kmau6zKhgT676hGgczD5VMdRMyJZFA=")
            
            .build()
    }
    
    /**
     * Configures OkHttpClient with certificate pinning and security settings
     */
    fun configureSecureClient(): OkHttpClient.Builder {
        return OkHttpClient.Builder()
            .certificatePinner(createCertificatePinner())
            .addInterceptor(SecurityInterceptor())
            .addNetworkInterceptor(TLSVersionInterceptor())
    }
}

/**
 * Security interceptor for additional network security checks
 */
class SecurityInterceptor : okhttp3.Interceptor {
    override fun intercept(chain: okhttp3.Interceptor.Chain): okhttp3.Response {
        val request = chain.request()
        
        // Add security headers
        val secureRequest = request.newBuilder()
            .addHeader("X-Requested-With", "XMLHttpRequest")
            .addHeader("Cache-Control", "no-cache, no-store, must-revalidate")
            .addHeader("Pragma", "no-cache")
            .addHeader("Expires", "0")
            .build()
        
        return chain.proceed(secureRequest)
    }
}

/**
 * Interceptor to enforce minimum TLS version
 */
class TLSVersionInterceptor : okhttp3.Interceptor {
    override fun intercept(chain: okhttp3.Interceptor.Chain): okhttp3.Response {
        val connection = chain.connection()
        
        // Ensure we're using TLS 1.2 or higher
        if (connection?.handshake()?.tlsVersion != null) {
            val tlsVersion = connection.handshake()?.tlsVersion.toString()
            if (!tlsVersion.contains("TLS_1_2") && !tlsVersion.contains("TLS_1_3")) {
                throw SecurityException("Insecure TLS version detected: $tlsVersion")
            }
        }
        
        return chain.proceed(chain.request())
    }
}