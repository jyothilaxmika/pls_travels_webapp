package com.plstravels.driver.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// PLS Travels Brand Colors
private val PLSBlue = Color(0xFF1976D2)
private val PLSBlueVariant = Color(0xFF1565C0)
private val PLSCyan = Color(0xFF00BCD4)
private val PLSYellow = Color(0xFFFFC107)
private val PLSGreen = Color(0xFF4CAF50)
private val PLSRed = Color(0xFFE53935)

private val DarkColorScheme = darkColorScheme(
    primary = PLSBlue,
    secondary = PLSCyan,
    tertiary = PLSYellow,
    background = Color(0xFF121212),
    surface = Color(0xFF1E1E1E),
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onTertiary = Color.Black,
    onBackground = Color.White,
    onSurface = Color.White,
    error = PLSRed,
    onError = Color.White
)

private val LightColorScheme = lightColorScheme(
    primary = PLSBlue,
    secondary = PLSCyan,
    tertiary = PLSYellow,
    background = Color(0xFFFDFDFD),
    surface = Color.White,
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onTertiary = Color.Black,
    onBackground = Color.Black,
    onSurface = Color.Black,
    error = PLSRed,
    onError = Color.White
)

@Composable
fun PLSTravelsTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}