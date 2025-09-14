package com.plstravels.driver.di

import com.plstravels.driver.BuildConfig
import com.plstravels.driver.data.network.ApiService
import com.plstravels.driver.data.network.AuthInterceptor
import com.plstravels.driver.data.network.RefreshApiService
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Named
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

/**
 * Hilt module for network dependencies
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    
    @Provides
    @Singleton
    @Named("base")
    fun provideBaseOkHttpClient(): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
        
        if (BuildConfig.DEBUG) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            builder.addInterceptor(loggingInterceptor)
        }
        
        return builder.build()
    }
    
    @Provides
    @Singleton
    @Named("auth")
    fun provideAuthOkHttpClient(@Named("base") baseOkHttpClient: OkHttpClient, authInterceptor: AuthInterceptor): OkHttpClient {
        return baseOkHttpClient.newBuilder()
            .addInterceptor(authInterceptor)
            .build()
    }
    
    @Provides
    @Singleton
    @Named("auth")
    fun provideAuthRetrofit(@Named("auth") okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
    
    @Provides
    @Singleton
    @Named("refresh")
    fun provideRefreshRetrofit(@Named("base") okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
    
    @Provides
    @Singleton
    fun provideApiService(@Named("auth") retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }
    
    @Provides
    @Singleton
    fun provideRefreshApiService(@Named("refresh") retrofit: Retrofit): RefreshApiService {
        return retrofit.create(RefreshApiService::class.java)
    }
}