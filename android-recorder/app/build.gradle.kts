import java.util.Properties

plugins {
    id("com.android.application")
}

// Release signing key lives outside the repo (see ~/sound-monitor-release-key/README.txt).
val keyProps = Properties().apply {
    val f = file(System.getProperty("user.home") + "/sound-monitor-release-key/keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "org.soundmonitor.recorder"
    compileSdk = 36

    defaultConfig {
        applicationId = "org.soundmonitor.recorder"
        minSdk = 19          // Android 4.4 (experimental: sound + video via the old Camera API, TLS via Conscrypt) and newer
        targetSdk = 36
        versionCode = 3
        versionName = "1.2"
    }

    signingConfigs {
        if (keyProps.containsKey("storeFile")) {
            create("release") {
                storeFile = file(keyProps.getProperty("storeFile"))
                storePassword = keyProps.getProperty("storePassword")
                keyAlias = keyProps.getProperty("keyAlias")
                keyPassword = keyProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    // Android 4.4 has no TLS cipher Hugging Face accepts; Conscrypt brings a modern TLS stack (used below Android 5 only).
    implementation("org.conscrypt:conscrypt-android:2.5.3")
}
