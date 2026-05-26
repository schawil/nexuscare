// build.gradle.kts — RACINE du projet (pas celui dans app/)
// Pas d'alias libs ici — versions déclarées directement
plugins {
    id("com.android.application")        version "8.7.3"  apply false
    id("com.android.library")            version "8.7.3"  apply false
    id("org.jetbrains.kotlin.android")    version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
}
