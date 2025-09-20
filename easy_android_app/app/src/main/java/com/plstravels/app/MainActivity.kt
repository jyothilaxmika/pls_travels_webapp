package com.plstravels.app

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Bitmap
import android.os.Bundle
import android.view.View
import android.webkit.*
import android.widget.ProgressBar

class MainActivity : Activity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    
    // Your PLS TRAVELS web app URL
    private val APP_URL = "https://4a66a697-148e-4a5f-b608-7aec82b1961e-00-3264w7moy943g.spock.replit.dev"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        progressBar = findViewById(R.id.progressBar)

        // Enable JavaScript
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.loadWithOverviewMode = true
        webView.settings.useWideViewPort = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = true
        
        // Enable zoom controls
        webView.settings.setSupportZoom(true)
        webView.settings.builtInZoomControls = true
        webView.settings.displayZoomControls = false

        // Set WebView client
        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                progressBar.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                progressBar.visibility = View.GONE
            }

            override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                if (url?.startsWith("http") == true) {
                    view?.loadUrl(url)
                    return true
                }
                return false
            }
        }

        // Set WebChrome client for better functionality
        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress < 100) {
                    progressBar.visibility = View.VISIBLE
                } else {
                    progressBar.visibility = View.GONE
                }
            }
        }

        // Load your web app
        webView.loadUrl(APP_URL)
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}