package com.plstravels.driver.di

import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.plstravels.driver.BuildConfig
import com.plstravels.driver.data.api.AuthApi
import com.plstravels.driver.data.api.DutyApi
import com.plstravels.driver.data.api.interceptor.AuthInterceptor
import com.plstravels.driver.data.api.interceptor.CertificatePinningInterceptor
import com.plstravels.driver.data.repository.AuthRepository
import com.plstravels.driver.data.repository.DutyRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

/**
 * Dependency injection module for network components
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideGson(): Gson {
        return GsonBuilder()
            .setDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'")
            .setLenient()
            .create()
    }

    @Provides
    @Singleton
    fun provideHttpLoggingInterceptor(): HttpLoggingInterceptor {
        return HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }
    }

    @Provides
    @Singleton
    fun provideCertificatePinningInterceptor(): CertificatePinningInterceptor {
        return CertificatePinningInterceptor()
    }

    @Provides
    @Singleton
    fun provideAuthInterceptor(authRepository: AuthRepository): AuthInterceptor {
        return AuthInterceptor(authRepository)
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(
        loggingInterceptor: HttpLoggingInterceptor,
        certificatePinningInterceptor: CertificatePinningInterceptor,
        authInterceptor: AuthInterceptor
    ): OkHttpClient {
        return OkHttpClient.Builder()
            .addInterceptor(loggingInterceptor)
            .addInterceptor(authInterceptor)
            .apply {
                // Add certificate pinning only in release builds
                if (BuildConfig.CERTIFICATE_PINNING_ENABLED) {
                    addInterceptor(certificatePinningInterceptor)
                }
            }
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(
        okHttpClient: OkHttpClient,
        gson: Gson
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
    }

    @Provides
    @Singleton
    fun provideAuthApi(retrofit: Retrofit): AuthApi {
        return retrofit.create(AuthApi::class.java)
    }

    @Provides
    @Singleton
    fun provideDutyApi(retrofit: Retrofit): DutyApi {
        return retrofit.create(DutyApi::class.java)
    }
}