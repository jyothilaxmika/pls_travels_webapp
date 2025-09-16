package com.plstravels.driver.data.api.interceptor

import com.plstravels.driver.BuildConfig
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Interceptor for certificate pinning (disabled for development)
 */
@Singleton
class CertificatePinningInterceptor @Inject constructor() : Interceptor {
    
    override fun intercept(chain: Interceptor.Chain): Response {
        // Certificate pinning disabled for development builds
        // In production, this would validate SSL certificates
        return if (BuildConfig.CERTIFICATE_PINNING_ENABLED) {
            // In production builds, add certificate validation logic here
            // For now, just proceed normally
            chain.proceed(chain.request())
        } else {
            // Development builds skip certificate pinning
            chain.proceed(chain.request())
        }
    }
}