plugins {
    id("com.android.application")
}

android {
    namespace = "org.soundmonitor.recorder"
    compileSdk = 36

    defaultConfig {
        applicationId = "org.soundmonitor.recorder"
        minSdk = 22          // Fire OS 5 (Android 5.1) and newer
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
