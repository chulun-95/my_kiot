# Android POS — Phase 1: Backend Mobile Auth + App Foundation + Login

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an Android app the user can log into against the existing FastAPI backend, with a solid networking/auth foundation (token storage, auto-refresh) and a 4-tab navigation shell ready for feature work.

**Architecture:** Native Kotlin app (`android/`) using Jetpack Compose + MVVM + Hilt + Retrofit, online-only. Backend gains 3 mobile auth endpoints (`/api/v1/auth/mobile/login|refresh|logout`) that reuse the existing `auth_service` but return/accept the refresh token in the JSON body instead of an HttpOnly cookie. The app stores tokens in EncryptedSharedPreferences and auto-refreshes on 401 via an OkHttp `Authenticator`.

**Tech Stack:** Python/FastAPI/pytest (backend); Kotlin 2.1, Gradle Kotlin DSL, Jetpack Compose, Hilt 2.52, Retrofit 2.11 + OkHttp 4.12 + kotlinx.serialization, androidx.security-crypto, JUnit4 + MockK + Turbine + kotlinx-coroutines-test + OkHttp MockWebServer (tests).

This is **Phase 1 of 4**. Subsequent phases (POS+hardware, goods receipt, inventory+reports) get their own plans after this one is implemented.

---

## File Structure

**Backend (modify/create):**
- Modify: `backend/modules/auth/router.py` — add 3 mobile endpoints
- Create: `tests/test_auth_mobile.py` — endpoint tests

**Android (all new, under `android/`):**
- `android/settings.gradle.kts`, `android/build.gradle.kts`, `android/gradle.properties`, `android/gradle/libs.versions.toml` — build config
- `android/app/build.gradle.kts`, `android/app/proguard-rules.pro`
- `android/app/src/main/AndroidManifest.xml`
- `android/app/src/main/java/com/mykiot/pos/MyKiotApp.kt` — `@HiltAndroidApp`
- `android/app/src/main/java/com/mykiot/pos/MainActivity.kt`
- `core/network/` — `dto/AuthDtos.kt`, `ApiResult.kt`, `ApiError.kt`, `ErrorMapper.kt`, `AuthApi.kt`, `AuthInterceptor.kt`, `TokenAuthenticator.kt`, `NetworkModule.kt`
- `core/auth/` — `TokenStore.kt` (interface), `EncryptedTokenStore.kt` (impl), `AuthRepository.kt`, `SessionState.kt`, `AuthModule.kt`
- `core/ui/` — `theme/` (Color, Theme, Type), `Money.kt`
- `feature/auth/` — `LoginViewModel.kt`, `LoginScreen.kt`
- `navigation/` — `AppNav.kt`, `Routes.kt`, `HomeScaffold.kt`
- Tests under `android/app/src/test/java/com/mykiot/pos/` mirroring the above

---

## Task 1: Backend — mobile auth endpoints

The existing `auth_service.login / refresh_tokens / logout` already produce the refresh token; the web router only hides it (`response_model_exclude={"refresh_token"}`) and sets it as a cookie. The mobile endpoints reuse the same service and the existing `RefreshRequest` / `LogoutRequest` schemas, returning the token in the body.

**Files:**
- Modify: `backend/modules/auth/router.py`
- Test: `tests/test_auth_mobile.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_auth_mobile.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio


async def _register(client):
    payload = {
        "shop_name": "Tap Hoa Mobile",
        "owner_name": "Owner Mobile",
        "phone": "0907654321",
        "password": "secret123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return payload


async def test_mobile_login_returns_refresh_token_in_body(client):
    creds = await _register(client)
    resp = await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]            # body, NOT cookie
    assert data["user"]["role"] == "OWNER"
    assert data["tenant"]["id"]
    # mobile endpoint must NOT set the web refresh cookie
    assert resp.cookies.get("refresh_token") is None


async def test_mobile_login_wrong_password_401(client):
    creds = await _register(client)
    resp = await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": "wrong-pass"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_mobile_refresh_rotates_and_returns_new_token(client):
    creds = await _register(client)
    login = (await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": creds["password"]},
    )).json()
    old_refresh = login["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/mobile/refresh", json={"refresh_token": old_refresh}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"] and data["refresh_token"] != old_refresh

    # old token is now invalid (rotation deletes it)
    reuse = await client.post(
        "/api/v1/auth/mobile/refresh", json={"refresh_token": old_refresh}
    )
    assert reuse.status_code == 401


async def test_mobile_refresh_invalid_token_401(client):
    resp = await client.post(
        "/api/v1/auth/mobile/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_mobile_logout_revokes_refresh_token(client):
    creds = await _register(client)
    login = (await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": creds["password"]},
    )).json()

    resp = await client.post(
        "/api/v1/auth/mobile/logout",
        json={"refresh_token": login["refresh_token"]},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert resp.status_code == 200

    # refresh with the logged-out token must fail
    after = await client.post(
        "/api/v1/auth/mobile/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert after.status_code == 401


async def test_mobile_logout_requires_auth(client):
    resp = await client.post(
        "/api/v1/auth/mobile/logout", json={"refresh_token": "x"}
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth_mobile.py -v`
Expected: FAIL — all 404 (endpoints not defined yet).

- [ ] **Step 3: Add the mobile endpoints**

In `backend/modules/auth/router.py`, add `RefreshRequest` and `LogoutRequest` to the schema import block (lines 18-30), so it reads:

```python
from backend.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginSuccessResponse,
    LoginTenantSelectionResponse,
    LogoutRequest,
    MeResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TenantBrief,
    TokenPair,
    UserBrief,
)
```

Then append these endpoints at the end of the file (after `me`, line 127). Note: NO `response_model_exclude` (we want the refresh token in the body), and the same `@limiter.limit` on login as the web route:

```python
# ---------- mobile (native app) ----------
# Same service as web, but returns/accepts the refresh token in the JSON body
# instead of an HttpOnly cookie (native clients have no cookie jar by default).

@router.post(
    "/mobile/login",
    response_model=Union[LoginSuccessResponse, LoginTenantSelectionResponse],
)
@limiter.limit("5/5minute")
async def mobile_login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.login(db, payload)


@router.post("/mobile/refresh", response_model=LoginSuccessResponse)
async def mobile_refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.refresh_tokens(db, payload.refresh_token)


@router.post("/mobile/logout", response_model=MessageResponse)
async def mobile_logout(
    payload: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    await auth_service.logout(db, user.id, payload.refresh_token)
    return MessageResponse(message="Đăng xuất thành công")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth_mobile.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full auth suite to confirm no regression**

Run: `python -m pytest tests/test_auth.py tests/test_auth_mobile.py -v`
Expected: PASS (existing web auth tests + new mobile tests all green).

- [ ] **Step 6: Commit**

```bash
git add backend/modules/auth/router.py tests/test_auth_mobile.py
git commit -m "feat(auth): mobile auth endpoints trả token trong body cho app native"
```

---

## Task 2: Android — project scaffold (Gradle + Hilt + Compose)

Pure configuration task: a buildable empty app. No business logic yet. Verification is a successful Gradle build.

> **Prereq for the implementer:** Android SDK + JDK 17 installed; `ANDROID_HOME` set. From `android/`, the Gradle wrapper is used (`./gradlew` / `gradlew.bat`). If the wrapper jar is absent, run `gradle wrapper --gradle-version 8.11` once (requires a local Gradle), or copy a wrapper from any recent Android Studio project.

**Files:**
- Create: `android/settings.gradle.kts`
- Create: `android/build.gradle.kts`
- Create: `android/gradle.properties`
- Create: `android/gradle/libs.versions.toml`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/proguard-rules.pro`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/java/com/mykiot/pos/MyKiotApp.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/MainActivity.kt`
- Create: `android/app/src/main/res/values/strings.xml`
- Create: `android/.gitignore`

- [ ] **Step 1: Create `android/gradle/libs.versions.toml`**

```toml
[versions]
agp = "8.7.3"
kotlin = "2.1.0"
ksp = "2.1.0-1.0.29"
hilt = "2.52"
hiltNavigation = "1.2.0"
composeBom = "2024.12.01"
activityCompose = "1.9.3"
lifecycle = "2.8.7"
navigation = "2.8.5"
retrofit = "2.11.0"
okhttp = "4.12.0"
serialization = "1.7.3"
retrofitSerialization = "1.0.0"
securityCrypto = "1.1.0-alpha06"
coreKtx = "1.15.0"
junit = "4.13.2"
mockk = "1.13.13"
turbine = "1.2.0"
coroutinesTest = "1.9.0"

[libraries]
androidx-core-ktx = { module = "androidx.core:core-ktx", version.ref = "coreKtx" }
androidx-activity-compose = { module = "androidx.activity:activity-compose", version.ref = "activityCompose" }
androidx-lifecycle-runtime-compose = { module = "androidx.lifecycle:lifecycle-runtime-compose", version.ref = "lifecycle" }
androidx-lifecycle-viewmodel-compose = { module = "androidx.lifecycle:lifecycle-viewmodel-compose", version.ref = "lifecycle" }
compose-bom = { module = "androidx.compose:compose-bom", version.ref = "composeBom" }
compose-ui = { module = "androidx.compose.ui:ui" }
compose-ui-graphics = { module = "androidx.compose.ui:ui-graphics" }
compose-ui-tooling = { module = "androidx.compose.ui:ui-tooling" }
compose-ui-tooling-preview = { module = "androidx.compose.ui:ui-tooling-preview" }
compose-material3 = { module = "androidx.compose.material3:material3" }
compose-material-icons = { module = "androidx.compose.material:material-icons-extended" }
navigation-compose = { module = "androidx.navigation:navigation-compose", version.ref = "navigation" }
hilt-android = { module = "com.google.dagger:hilt-android", version.ref = "hilt" }
hilt-compiler = { module = "com.google.dagger:hilt-compiler", version.ref = "hilt" }
hilt-navigation-compose = { module = "androidx.hilt:hilt-navigation-compose", version.ref = "hiltNavigation" }
retrofit = { module = "com.squareup.retrofit2:retrofit", version.ref = "retrofit" }
okhttp = { module = "com.squareup.okhttp3:okhttp", version.ref = "okhttp" }
okhttp-logging = { module = "com.squareup.okhttp3:logging-interceptor", version.ref = "okhttp" }
kotlinx-serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "serialization" }
retrofit-serialization = { module = "com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter", version.ref = "retrofitSerialization" }
security-crypto = { module = "androidx.security:security-crypto", version.ref = "securityCrypto" }
# test
junit = { module = "junit:junit", version.ref = "junit" }
mockk = { module = "io.mockk:mockk", version.ref = "mockk" }
turbine = { module = "app.cash.turbine:turbine", version.ref = "turbine" }
coroutines-test = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-test", version.ref = "coroutinesTest" }
okhttp-mockwebserver = { module = "com.squareup.okhttp3:mockwebserver", version.ref = "okhttp" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
hilt = { id = "com.google.dagger.hilt.android", version.ref = "hilt" }
```

- [ ] **Step 2: Create root build files**

`android/settings.gradle.kts`:

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "MyKiotPos"
include(":app")
```

`android/build.gradle.kts`:

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
}
```

`android/gradle.properties`:

```properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
```

`android/.gitignore`:

```gitignore
*.iml
.gradle/
local.properties
.idea/
build/
captures/
.externalNativeBuild/
.cxx/
*.apk
*.keystore
```

- [ ] **Step 3: Create `android/app/build.gradle.kts`**

```kotlin
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

// Read API base URL from local.properties (not committed), with safe defaults.
val localProps = Properties().apply {
    val f = rootProject.file("local.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}
fun prop(key: String, default: String) = (localProps.getProperty(key) ?: default)

android {
    namespace = "com.mykiot.pos"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.mykiot.pos"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            buildConfigField("String", "BASE_URL", "\"${prop("BASE_URL_DEBUG", "http://10.0.2.2:8000/api/v1/")}\"")
        }
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            buildConfigField("String", "BASE_URL", "\"${prop("BASE_URL_RELEASE", "https://api.example.com/api/v1/")}\"")
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)

    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.graphics)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons)
    debugImplementation(libs.compose.ui.tooling)

    implementation(libs.navigation.compose)
    implementation(libs.hilt.navigation.compose)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)

    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.security.crypto)

    testImplementation(libs.junit)
    testImplementation(libs.mockk)
    testImplementation(libs.turbine)
    testImplementation(libs.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)
}
```

`android/app/proguard-rules.pro` (keep kotlinx.serialization metadata):

```proguard
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keep,includedescriptorclasses class com.mykiot.pos.**$$serializer { *; }
-keepclassmembers class com.mykiot.pos.** { *** Companion; }
-keepclasseswithmembers class com.mykiot.pos.** { kotlinx.serialization.KSerializer serializer(...); }
```

- [ ] **Step 4: Create manifest + strings + Application + Activity**

`android/app/src/main/AndroidManifest.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:name=".MyKiotApp"
        android:allowBackup="false"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.Material.Light.NoActionBar"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

> Note: `usesCleartextTraffic="true"` is for the debug emulator hitting `http://10.0.2.2:8000`. Acceptable for Phase 1; release uses HTTPS. A later phase can split this into a debug-only manifest.

`android/app/src/main/res/values/strings.xml`:

```xml
<resources>
    <string name="app_name">My Kiot POS</string>
</resources>
```

`android/app/src/main/java/com/mykiot/pos/MyKiotApp.kt`:

```kotlin
package com.mykiot.pos

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class MyKiotApp : Application()
```

`android/app/src/main/java/com/mykiot/pos/MainActivity.kt` (temporary body, replaced in Task 7):

```kotlin
package com.mykiot.pos

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface { Text("My Kiot POS") }
            }
        }
    }
}
```

- [ ] **Step 5: Build the project**

Run (from `android/`): `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL. (First run downloads dependencies.)

- [ ] **Step 6: Commit**

```bash
git add android/
git commit -m "chore(android): scaffold project Compose + Hilt + Retrofit (buildable shell)"
```

---

## Task 3: Core network — DTOs, ApiResult, ErrorMapper, AuthApi

The backend error body is `{"error": {"code", "message", "details"}}`. The `ErrorMapper` turns any failure (HTTP error body, network exception) into a Vietnamese-facing `ApiError`. This is the one piece of pure logic we TDD here.

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/dto/AuthDtos.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/ApiError.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/ApiResult.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/ErrorMapper.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/AuthApi.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/core/network/ErrorMapperTest.kt`

- [ ] **Step 1: Create the DTOs**

`core/network/dto/AuthDtos.kt`:

```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class MobileLoginRequest(
    val phone: String,
    val password: String,
    @SerialName("tenant_id") val tenantId: Long? = null,
)

@Serializable
data class RefreshRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class LogoutRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class UserDto(
    val id: Long,
    @SerialName("full_name") val fullName: String,
    val phone: String? = null,
    val email: String? = null,
    val role: String,
)

@Serializable
data class TenantDto(
    val id: Long,
    val name: String,
    val slug: String,
)

@Serializable
data class TenantOptionDto(
    val id: Long,
    val name: String,
    val role: String,
)

/**
 * /auth/mobile/login may return EITHER a success body OR a tenant-selection body
 * (when the phone exists in multiple shops and no tenant_id was provided).
 * Both shapes are optional-field unions parsed from the same JSON object.
 */
@Serializable
data class LoginResponseDto(
    // success fields
    val user: UserDto? = null,
    val tenant: TenantDto? = null,
    @SerialName("access_token") val accessToken: String? = null,
    @SerialName("refresh_token") val refreshToken: String? = null,
    // tenant-selection fields
    @SerialName("requires_tenant_selection") val requiresTenantSelection: Boolean = false,
    val tenants: List<TenantOptionDto>? = null,
)

@Serializable
data class TokenRefreshDto(
    val user: UserDto,
    val tenant: TenantDto,
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
)
```

- [ ] **Step 2: Create ApiError + ApiResult**

`core/network/ApiError.kt`:

```kotlin
package com.mykiot.pos.core.network

/** A failure already translated to a user-facing Vietnamese message. */
data class ApiError(
    val code: String,
    val message: String,
    val httpStatus: Int? = null,
)
```

`core/network/ApiResult.kt`:

```kotlin
package com.mykiot.pos.core.network

sealed interface ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>
    data class Failure(val error: ApiError) : ApiResult<Nothing>
}

inline fun <T> ApiResult<T>.onSuccess(block: (T) -> Unit): ApiResult<T> {
    if (this is ApiResult.Success) block(data)
    return this
}

inline fun <T> ApiResult<T>.onFailure(block: (ApiError) -> Unit): ApiResult<T> {
    if (this is ApiResult.Failure) block(error)
    return this
}
```

- [ ] **Step 3: Write the failing ErrorMapper test**

`core/network/ErrorMapperTest.kt`:

```kotlin
package com.mykiot.pos.core.network

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException

class ErrorMapperTest {

    private val mapper = ErrorMapper()

    private fun httpException(status: Int, body: String): HttpException {
        val response = Response.error<Any>(
            status,
            body.toResponseBody("application/json".toMediaType()),
        )
        return HttpException(response)
    }

    @Test
    fun `parses backend error body and prefers its vietnamese message`() {
        val ex = httpException(
            401,
            """{"error":{"code":"INVALID_CREDENTIALS","message":"Sai số điện thoại hoặc mật khẩu"}}""",
        )
        val err = mapper.map(ex)
        assertEquals("INVALID_CREDENTIALS", err.code)
        assertEquals("Sai số điện thoại hoặc mật khẩu", err.message)
        assertEquals(401, err.httpStatus)
    }

    @Test
    fun `network IOException maps to connection message`() {
        val err = mapper.map(IOException("timeout"))
        assertEquals("NETWORK_ERROR", err.code)
        assertEquals("Mất kết nối mạng, vui lòng thử lại", err.message)
    }

    @Test
    fun `unparseable error body falls back to generic vietnamese message`() {
        val ex = httpException(500, "<html>boom</html>")
        val err = mapper.map(ex)
        assertEquals("UNKNOWN", err.code)
        assertEquals("Có lỗi xảy ra, vui lòng thử lại", err.message)
        assertEquals(500, err.httpStatus)
    }
}
```

- [ ] **Step 4: Run the test to verify it fails**

Run (from `android/`): `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.network.ErrorMapperTest"`
Expected: FAIL — `ErrorMapper` unresolved reference.

- [ ] **Step 5: Implement ErrorMapper**

`core/network/ErrorMapper.kt`:

```kotlin
package com.mykiot.pos.core.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ErrorMapper @Inject constructor() {

    private val json = Json { ignoreUnknownKeys = true }

    fun map(throwable: Throwable): ApiError = when (throwable) {
        is HttpException -> mapHttp(throwable)
        is IOException -> ApiError("NETWORK_ERROR", "Mất kết nối mạng, vui lòng thử lại")
        else -> ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại")
    }

    private fun mapHttp(ex: HttpException): ApiError {
        val status = ex.code()
        val raw = runCatching { ex.response()?.errorBody()?.string() }.getOrNull()
        val parsed = raw?.let { runCatching { json.decodeFromString<ErrorEnvelope>(it) }.getOrNull() }
        val body = parsed?.error
        return if (body != null && body.message.isNotBlank()) {
            ApiError(body.code.ifBlank { "UNKNOWN" }, body.message, status)
        } else {
            ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại", status)
        }
    }

    @Serializable
    private data class ErrorEnvelope(val error: ErrorBody? = null)

    @Serializable
    private data class ErrorBody(
        val code: String = "",
        val message: String = "",
        @SerialName("details") val details: Map<String, String>? = null,
    )
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.network.ErrorMapperTest"`
Expected: PASS (3 tests).

- [ ] **Step 7: Create the Retrofit AuthApi**

`core/network/AuthApi.kt`:

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.LoginResponseDto
import com.mykiot.pos.core.network.dto.LogoutRequest
import com.mykiot.pos.core.network.dto.MobileLoginRequest
import com.mykiot.pos.core.network.dto.RefreshRequest
import com.mykiot.pos.core.network.dto.TokenRefreshDto
import retrofit2.http.Body
import retrofit2.http.POST

interface AuthApi {

    @POST("auth/mobile/login")
    suspend fun login(@Body body: MobileLoginRequest): LoginResponseDto

    @POST("auth/mobile/refresh")
    suspend fun refresh(@Body body: RefreshRequest): TokenRefreshDto

    @POST("auth/mobile/logout")
    suspend fun logout(@Body body: LogoutRequest)
}
```

- [ ] **Step 8: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/ android/app/src/test/
git commit -m "feat(android): DTOs, ApiResult, ErrorMapper (VN messages), AuthApi"
```

---

## Task 4: Token storage (EncryptedSharedPreferences behind an interface)

`TokenStore` is an interface so ViewModels/interceptors depend on the abstraction and tests use a fake. The encrypted implementation needs Android, so its real behavior is covered by an instrumented test (noted, not blocking); JVM tests use a fake.

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/auth/TokenStore.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/auth/EncryptedTokenStore.kt`
- Create: `android/app/src/test/java/com/mykiot/pos/core/auth/FakeTokenStore.kt`
- Create: `android/app/src/test/java/com/mykiot/pos/core/auth/FakeTokenStoreTest.kt`

- [ ] **Step 1: Define the TokenStore interface**

`core/auth/TokenStore.kt`:

```kotlin
package com.mykiot.pos.core.auth

interface TokenStore {
    fun getAccessToken(): String?
    fun getRefreshToken(): String?
    fun save(accessToken: String, refreshToken: String)
    fun clear()
    fun hasSession(): Boolean
}
```

- [ ] **Step 2: Write the failing fake + its contract test**

`core/auth/FakeTokenStore.kt` (test source set):

```kotlin
package com.mykiot.pos.core.auth

class FakeTokenStore : TokenStore {
    private var access: String? = null
    private var refresh: String? = null

    override fun getAccessToken(): String? = access
    override fun getRefreshToken(): String? = refresh
    override fun save(accessToken: String, refreshToken: String) {
        access = accessToken; refresh = refreshToken
    }
    override fun clear() { access = null; refresh = null }
    override fun hasSession(): Boolean = access != null && refresh != null
}
```

`core/auth/FakeTokenStoreTest.kt`:

```kotlin
package com.mykiot.pos.core.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class FakeTokenStoreTest {

    @Test
    fun `save then read returns tokens and hasSession true`() {
        val store = FakeTokenStore()
        assertFalse(store.hasSession())
        store.save("acc", "ref")
        assertEquals("acc", store.getAccessToken())
        assertEquals("ref", store.getRefreshToken())
        assertTrue(store.hasSession())
    }

    @Test
    fun `clear wipes tokens`() {
        val store = FakeTokenStore()
        store.save("acc", "ref")
        store.clear()
        assertNull(store.getAccessToken())
        assertNull(store.getRefreshToken())
        assertFalse(store.hasSession())
    }
}
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.auth.FakeTokenStoreTest"`
Expected: FAIL — `TokenStore` / `FakeTokenStore` unresolved (interface created in Step 1, fake in Step 2 — fails only if interface signature mismatches; if Step 1+2 already compile, this run should PASS). If it passes immediately, that is acceptable for this fake-contract task — proceed.

- [ ] **Step 4: Implement EncryptedTokenStore**

`core/auth/EncryptedTokenStore.kt`:

```kotlin
package com.mykiot.pos.core.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class EncryptedTokenStore @Inject constructor(
    context: Context,
) : TokenStore {

    private val prefs = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "mykiot_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    override fun getAccessToken(): String? = prefs.getString(KEY_ACCESS, null)
    override fun getRefreshToken(): String? = prefs.getString(KEY_REFRESH, null)

    override fun save(accessToken: String, refreshToken: String) {
        prefs.edit().putString(KEY_ACCESS, accessToken).putString(KEY_REFRESH, refreshToken).apply()
    }

    override fun clear() {
        prefs.edit().clear().apply()
    }

    override fun hasSession(): Boolean = getAccessToken() != null && getRefreshToken() != null

    private companion object {
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
    }
}
```

- [ ] **Step 5: Run the fake test to verify it passes**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.auth.FakeTokenStoreTest"`
Expected: PASS (2 tests).

> **Deferred verification:** the real `EncryptedTokenStore` (encryption round-trip) is covered by an instrumented test added in Phase 2's hardware/QA pass, or can be manually verified once Login works in Task 7. Not blocking Phase 1.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/auth/ android/app/src/test/java/com/mykiot/pos/core/auth/
git commit -m "feat(android): TokenStore interface + EncryptedSharedPreferences impl"
```

---

## Task 5: AuthInterceptor + TokenAuthenticator (single-flight refresh)

`AuthInterceptor` attaches the bearer token and the `X-Requested-With` header. `TokenAuthenticator` (OkHttp `Authenticator`) reacts to a 401 by refreshing once (single-flight via a lock) and retrying. Tested end-to-end with `MockWebServer`.

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/AuthInterceptor.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/TokenAuthenticator.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/core/network/TokenAuthenticatorTest.kt`

- [ ] **Step 1: Implement AuthInterceptor**

`core/network/AuthInterceptor.kt`:

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.auth.TokenStore
import okhttp3.Interceptor
import okhttp3.Response

// Provided via NetworkModule (not @Inject) to avoid a duplicate Hilt binding.
class AuthInterceptor(
    private val tokenStore: TokenStore,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val builder = chain.request().newBuilder()
            .header("X-Requested-With", "XMLHttpRequest")
        tokenStore.getAccessToken()?.let { builder.header("Authorization", "Bearer $it") }
        return chain.proceed(builder.build())
    }
}
```

- [ ] **Step 2: Write the failing TokenAuthenticator test**

`core/network/TokenAuthenticatorTest.kt`:

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.auth.FakeTokenStore
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class TokenAuthenticatorTest {

    private lateinit var server: MockWebServer

    @Before fun setUp() { server = MockWebServer().apply { start() } }
    @After fun tearDown() { server.shutdown() }

    private fun clientWith(store: FakeTokenStore): OkHttpClient {
        val refreshApiProvider = { RefreshCaller { refreshToken ->
            // call the mock server's /auth/mobile/refresh directly (no DI here)
            val resp = OkHttpClient().newCall(
                Request.Builder()
                    .url(server.url("auth/mobile/refresh"))
                    .post(okhttp3.RequestBody.create(null, ByteArray(0)))
                    .header("X-Refresh", refreshToken)
                    .build(),
            ).execute()
            val newAccess = resp.header("X-New-Access")
            val newRefresh = resp.header("X-New-Refresh")
            resp.close()
            if (resp.isSuccessful && newAccess != null && newRefresh != null) {
                TokenPairResult(newAccess, newRefresh)
            } else null
        } }
        return OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor(store))
            .authenticator(TokenAuthenticator(store, refreshApiProvider))
            .build()
    }

    @Test
    fun `on 401 it refreshes once and retries with new token`() {
        val store = FakeTokenStore().apply { save("old-access", "old-refresh") }

        // 1) protected call -> 401
        server.enqueue(MockResponse().setResponseCode(401))
        // 2) refresh call -> 200 with new tokens
        server.enqueue(MockResponse().setResponseCode(200)
            .addHeader("X-New-Access", "new-access")
            .addHeader("X-New-Refresh", "new-refresh"))
        // 3) retried protected call -> 200
        server.enqueue(MockResponse().setResponseCode(200).setBody("ok"))

        val client = clientWith(store)
        val resp = client.newCall(
            Request.Builder().url(server.url("products")).build(),
        ).execute()

        assertEquals(200, resp.code)
        assertEquals("ok", resp.body?.string())
        resp.close()

        // store updated with rotated tokens
        assertEquals("new-access", store.getAccessToken())
        assertEquals("new-refresh", store.getRefreshToken())

        // first request used old token
        val first = server.takeRequest()
        assertEquals("Bearer old-access", first.getHeader("Authorization"))
        // refresh request carried the old refresh token
        val refresh = server.takeRequest()
        assertEquals("old-refresh", refresh.getHeader("X-Refresh"))
        // retried request used new token
        val retried = server.takeRequest()
        assertEquals("Bearer new-access", retried.getHeader("Authorization"))
    }

    @Test
    fun `when refresh fails it clears session and gives up`() {
        val store = FakeTokenStore().apply { save("old-access", "old-refresh") }
        server.enqueue(MockResponse().setResponseCode(401)) // protected -> 401
        server.enqueue(MockResponse().setResponseCode(401)) // refresh -> 401

        val client = clientWith(store)
        val resp = client.newCall(
            Request.Builder().url(server.url("products")).build(),
        ).execute()

        // OkHttp returns the last 401 once the authenticator returns null
        assertEquals(401, resp.code)
        resp.close()
        assertTrue(!store.hasSession())
    }
}
```

> The test injects a `RefreshCaller` lambda instead of a real Retrofit `AuthApi`, so the authenticator's logic is exercised without a DI graph. Production wiring passes a `RefreshCaller` backed by `AuthApi.refresh` (Task 6 / NetworkModule).

- [ ] **Step 3: Run the test to verify it fails**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.network.TokenAuthenticatorTest"`
Expected: FAIL — `TokenAuthenticator`, `RefreshCaller`, `TokenPairResult` unresolved.

- [ ] **Step 4: Implement TokenAuthenticator**

`core/network/TokenAuthenticator.kt`:

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.auth.TokenStore
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

/** Result of a successful token refresh. */
data class TokenPairResult(val accessToken: String, val refreshToken: String)

/** Performs the refresh network call; returns null on failure. */
fun interface RefreshCaller {
    fun refresh(refreshToken: String): TokenPairResult?
}

/**
 * On 401, refreshes the access token once (single-flight) and retries the request.
 * `refreshCallerProvider` is a provider to break the DI cycle (the refresh call uses
 * an OkHttp client that itself owns this authenticator).
 *
 * Provided via NetworkModule (not @Inject) to avoid a duplicate Hilt binding.
 */
class TokenAuthenticator(
    private val tokenStore: TokenStore,
    private val refreshCallerProvider: () -> RefreshCaller,
) : Authenticator {

    private val lock = Any()

    override fun authenticate(route: Route?, response: Response): Request? {
        // Give up if we've already retried once (avoid infinite loop).
        if (responseCount(response) >= 2) return null

        val currentRefresh = tokenStore.getRefreshToken() ?: return null
        val failedAccess = response.request.header("Authorization")

        synchronized(lock) {
            val latestAccess = tokenStore.getAccessToken()
            // Another thread already refreshed while we waited -> reuse new token.
            if (latestAccess != null && "Bearer $latestAccess" != failedAccess) {
                return response.request.newBuilder()
                    .header("Authorization", "Bearer $latestAccess")
                    .build()
            }

            val refreshed = refreshCallerProvider().refresh(currentRefresh)
            if (refreshed == null) {
                tokenStore.clear()
                return null
            }
            tokenStore.save(refreshed.accessToken, refreshed.refreshToken)
            return response.request.newBuilder()
                .header("Authorization", "Bearer ${refreshed.accessToken}")
                .build()
        }
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) { count++; prior = prior.priorResponse }
        return count
    }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.network.TokenAuthenticatorTest"`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/AuthInterceptor.kt android/app/src/main/java/com/mykiot/pos/core/network/TokenAuthenticator.kt android/app/src/test/java/com/mykiot/pos/core/network/TokenAuthenticatorTest.kt
git commit -m "feat(android): AuthInterceptor + single-flight TokenAuthenticator (401 auto-refresh)"
```

---

## Task 6: AuthRepository + LoginViewModel + Hilt modules

`AuthRepository` wraps `AuthApi` in `ApiResult`, persists tokens, and exposes session state. `LoginViewModel` drives the login screen state, including the multi-tenant selection branch. Both are TDD'd with a fake repository/api. Hilt modules wire the real graph.

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/auth/SessionState.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/auth/AuthRepository.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/auth/LoginViewModel.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/network/NetworkModule.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/core/auth/AuthModule.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/feature/auth/LoginViewModelTest.kt`

- [ ] **Step 1: Create SessionState + AuthRepository**

`core/auth/SessionState.kt`:

```kotlin
package com.mykiot.pos.core.auth

data class CurrentUser(
    val id: Long,
    val fullName: String,
    val role: String,    // "OWNER" | "CASHIER"
    val tenantId: Long,
    val tenantName: String,
)
```

`core/auth/AuthRepository.kt`:

```kotlin
package com.mykiot.pos.core.auth

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.AuthApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.dto.LoginResponseDto
import com.mykiot.pos.core.network.dto.LogoutRequest
import com.mykiot.pos.core.network.dto.MobileLoginRequest
import javax.inject.Inject
import javax.inject.Singleton

/** Outcome of a login attempt: either a session, or a tenant-selection prompt. */
sealed interface LoginOutcome {
    data class LoggedIn(val user: CurrentUser) : LoginOutcome
    data class NeedsTenant(val tenants: List<TenantChoice>) : LoginOutcome
}

data class TenantChoice(val id: Long, val name: String, val role: String)

@Singleton
class AuthRepository @Inject constructor(
    private val api: AuthApi,
    private val tokenStore: TokenStore,
    private val errorMapper: ErrorMapper,
) {
    fun hasSession(): Boolean = tokenStore.hasSession()

    suspend fun login(phone: String, password: String, tenantId: Long? = null): ApiResult<LoginOutcome> =
        try {
            val dto: LoginResponseDto = api.login(MobileLoginRequest(phone, password, tenantId))
            if (dto.requiresTenantSelection && dto.tenants != null) {
                ApiResult.Success(
                    LoginOutcome.NeedsTenant(
                        dto.tenants.map { TenantChoice(it.id, it.name, it.role) },
                    ),
                )
            } else if (dto.accessToken != null && dto.refreshToken != null &&
                dto.user != null && dto.tenant != null
            ) {
                tokenStore.save(dto.accessToken, dto.refreshToken)
                ApiResult.Success(
                    LoginOutcome.LoggedIn(
                        CurrentUser(
                            id = dto.user.id,
                            fullName = dto.user.fullName,
                            role = dto.user.role,
                            tenantId = dto.tenant.id,
                            tenantName = dto.tenant.name,
                        ),
                    ),
                )
            } else {
                ApiResult.Failure(ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại"))
            }
        } catch (t: Throwable) {
            ApiResult.Failure(errorMapper.map(t))
        }

    suspend fun logout() {
        val refresh = tokenStore.getRefreshToken()
        if (refresh != null) {
            runCatching { api.logout(LogoutRequest(refresh)) }
        }
        tokenStore.clear()
    }
}
```

- [ ] **Step 2: Write the failing LoginViewModel test**

`feature/auth/LoginViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.auth

import app.cash.turbine.test
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.LoginOutcome
import com.mykiot.pos.core.auth.TenantChoice
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import com.mykiot.pos.core.auth.AuthRepository

class LoginViewModelTest {

    private val repo: AuthRepository = mockk(relaxed = true)
    private val dispatcher = StandardTestDispatcher()

    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private fun user() = CurrentUser(1, "Owner", "OWNER", 10, "Shop")

    @Test
    fun `successful login emits Success state`() = runTest(dispatcher) {
        coEvery { repo.login("0901234567", "secret123", null) } returns
            ApiResult.Success(LoginOutcome.LoggedIn(user()))
        val vm = LoginViewModel(repo)

        vm.onPhoneChange("0901234567")
        vm.onPasswordChange("secret123")
        vm.state.test {
            assertEquals(LoginUiState(), awaitItem())   // initial
            vm.submit()
            assertEquals(true, awaitItem().loading)      // loading on
            val done = awaitItem()
            assertEquals(false, done.loading)
            assertTrue(done.loggedInUser != null)
            assertEquals("OWNER", done.loggedInUser?.role)
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun `invalid credentials emits vietnamese error`() = runTest(dispatcher) {
        coEvery { repo.login(any(), any(), null) } returns
            ApiResult.Failure(ApiError("INVALID_CREDENTIALS", "Sai số điện thoại hoặc mật khẩu", 401))
        val vm = LoginViewModel(repo)
        vm.onPhoneChange("0901234567"); vm.onPasswordChange("nope")

        vm.state.test {
            awaitItem() // initial
            vm.submit()
            awaitItem() // loading
            val err = awaitItem()
            assertEquals(false, err.loading)
            assertEquals("Sai số điện thoại hoặc mật khẩu", err.errorMessage)
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun `multi-tenant login surfaces tenant choices`() = runTest(dispatcher) {
        coEvery { repo.login(any(), any(), null) } returns
            ApiResult.Success(
                LoginOutcome.NeedsTenant(
                    listOf(TenantChoice(1, "Shop A", "OWNER"), TenantChoice(2, "Shop B", "CASHIER")),
                ),
            )
        val vm = LoginViewModel(repo)
        vm.onPhoneChange("0901234567"); vm.onPasswordChange("secret123")

        vm.state.test {
            awaitItem(); vm.submit(); awaitItem()
            val choose = awaitItem()
            assertEquals(2, choose.tenantChoices.size)
            assertEquals("Shop A", choose.tenantChoices.first().name)
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun `blank fields produce validation error without calling repo`() = runTest(dispatcher) {
        val vm = LoginViewModel(repo)
        vm.state.test {
            awaitItem()
            vm.submit()
            val err = awaitItem()
            assertEquals("Vui lòng nhập số điện thoại và mật khẩu", err.errorMessage)
            cancelAndIgnoreRemainingEvents()
        }
    }
}
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.auth.LoginViewModelTest"`
Expected: FAIL — `LoginViewModel`, `LoginUiState` unresolved.

- [ ] **Step 4: Implement LoginViewModel**

`feature/auth/LoginViewModel.kt`:

```kotlin
package com.mykiot.pos.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.auth.AuthRepository
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.LoginOutcome
import com.mykiot.pos.core.auth.TenantChoice
import com.mykiot.pos.core.network.ApiResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val phone: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val tenantChoices: List<TenantChoice> = emptyList(),
    val loggedInUser: CurrentUser? = null,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun onPhoneChange(v: String) = _state.update { it.copy(phone = v, errorMessage = null) }
    fun onPasswordChange(v: String) = _state.update { it.copy(password = v, errorMessage = null) }

    /** Submit with default tenant resolution. */
    fun submit() = doLogin(tenantId = null)

    /** Called after the user picks a shop from the tenant-selection list. */
    fun selectTenant(tenantId: Long) = doLogin(tenantId = tenantId)

    private fun doLogin(tenantId: Long?) {
        val s = _state.value
        if (s.phone.isBlank() || s.password.isBlank()) {
            _state.update { it.copy(errorMessage = "Vui lòng nhập số điện thoại và mật khẩu") }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null, tenantChoices = emptyList()) }
        viewModelScope.launch {
            when (val result = authRepository.login(s.phone.trim(), s.password, tenantId)) {
                is ApiResult.Success -> when (val outcome = result.data) {
                    is LoginOutcome.LoggedIn ->
                        _state.update { it.copy(loading = false, loggedInUser = outcome.user) }
                    is LoginOutcome.NeedsTenant ->
                        _state.update { it.copy(loading = false, tenantChoices = outcome.tenants) }
                }
                is ApiResult.Failure ->
                    _state.update { it.copy(loading = false, errorMessage = result.error.message) }
            }
        }
    }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.auth.LoginViewModelTest"`
Expected: PASS (4 tests).

- [ ] **Step 6: Wire Hilt modules**

`core/network/NetworkModule.kt`:

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.BuildConfig
import com.mykiot.pos.core.auth.TokenStore
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides @Singleton
    fun json(): Json = Json { ignoreUnknownKeys = true }

    @Provides @Singleton
    fun authInterceptor(tokenStore: TokenStore) = AuthInterceptor(tokenStore)

    /**
     * A bare client used ONLY for the refresh call, so the refresh request itself
     * cannot trigger the TokenAuthenticator (no infinite 401 loop).
     */
    @Provides @Singleton @RefreshClient
    fun refreshRetrofit(json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(OkHttpClient.Builder().build())
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides @Singleton
    fun refreshCallerProvider(@RefreshClient retrofit: Retrofit): () -> RefreshCaller {
        val api = retrofit.create(AuthApi::class.java)
        return {
            RefreshCaller { refreshToken ->
                runCatching {
                    kotlinx.coroutines.runBlocking {
                        val dto = api.refresh(com.mykiot.pos.core.network.dto.RefreshRequest(refreshToken))
                        TokenPairResult(dto.accessToken, dto.refreshToken)
                    }
                }.getOrNull()
            }
        }
    }

    @Provides @Singleton
    fun tokenAuthenticator(tokenStore: TokenStore, provider: () -> RefreshCaller) =
        TokenAuthenticator(tokenStore, provider)

    @Provides @Singleton
    fun okHttpClient(
        authInterceptor: AuthInterceptor,
        authenticator: TokenAuthenticator,
    ): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
            else HttpLoggingInterceptor.Level.NONE
        }
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .authenticator(authenticator)
            .build()
    }

    @Provides @Singleton
    fun retrofit(client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides @Singleton
    fun authApi(retrofit: Retrofit): AuthApi = retrofit.create(AuthApi::class.java)
}
```

Add the `@RefreshClient` qualifier — `core/network/RefreshClient.kt`:

```kotlin
package com.mykiot.pos.core.network

import javax.inject.Qualifier

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class RefreshClient
```

`core/auth/AuthModule.kt`:

```kotlin
package com.mykiot.pos.core.auth

import android.content.Context
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AuthModule {

    @Provides @Singleton
    fun tokenStore(@ApplicationContext context: Context): TokenStore =
        EncryptedTokenStore(context)
}
```

- [ ] **Step 7: Run the full unit-test suite + build**

Run: `./gradlew :app:testDebugUnitTest`
Expected: PASS (all unit tests).
Run: `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL (Hilt graph compiles).

- [ ] **Step 8: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ android/app/src/main/java/com/mykiot/pos/feature/auth/LoginViewModel.kt android/app/src/test/java/com/mykiot/pos/feature/auth/
git commit -m "feat(android): AuthRepository + LoginViewModel + Hilt network/auth modules"
```

---

## Task 7: Login screen + 4-tab navigation shell

The visible payoff: a Vietnamese Login screen and a 4-tab home (Bán · Nhập · Tồn · Báo cáo) with placeholder bodies. On launch, route to Home if a session exists, else Login. Compose UI is verified by build + manual run (no UI test framework added in Phase 1).

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/theme/Theme.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/auth/LoginScreen.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/navigation/Routes.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/navigation/HomeScaffold.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/navigation/AppNav.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/MainActivity.kt`

- [ ] **Step 1: Minimal Material3 theme**

`core/ui/theme/Theme.kt`:

```kotlin
package com.mykiot.pos.core.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF1565C0),
    secondary = Color(0xFF00897B),
)

@Composable
fun MyKiotTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = LightColors, content = content)
}
```

- [ ] **Step 2: Routes**

`navigation/Routes.kt`:

```kotlin
package com.mykiot.pos.navigation

object Routes {
    const val LOGIN = "login"
    const val HOME = "home"

    // bottom tabs
    const val TAB_POS = "tab_pos"
    const val TAB_RECEIPT = "tab_receipt"
    const val TAB_INVENTORY = "tab_inventory"
    const val TAB_REPORT = "tab_report"
}
```

- [ ] **Step 3: Login screen**

`feature/auth/LoginScreen.kt`:

```kotlin
package com.mykiot.pos.feature.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.auth.CurrentUser

@Composable
fun LoginScreen(
    onLoggedIn: (CurrentUser) -> Unit,
    viewModel: LoginViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.loggedInUser) {
        state.loggedInUser?.let(onLoggedIn)
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Đăng nhập", style = androidx.compose.material3.MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(24.dp))

        OutlinedTextField(
            value = state.phone,
            onValueChange = viewModel::onPhoneChange,
            label = { Text("Số điện thoại") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        )
        OutlinedTextField(
            value = state.password,
            onValueChange = viewModel::onPasswordChange,
            label = { Text("Mật khẩu") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        )

        state.errorMessage?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = androidx.compose.material3.MaterialTheme.colorScheme.error)
        }

        // Multi-tenant selection
        if (state.tenantChoices.isNotEmpty()) {
            Spacer(Modifier.height(12.dp))
            Text("Chọn cửa hàng:")
            state.tenantChoices.forEach { choice ->
                TextButton(onClick = { viewModel.selectTenant(choice.id) }) {
                    Text("${choice.name} (${choice.role})")
                }
            }
        }

        Spacer(Modifier.height(16.dp))
        Button(
            onClick = viewModel::submit,
            enabled = !state.loading,
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) {
            if (state.loading) CircularProgressIndicator(modifier = Modifier.height(24.dp))
            else Text("Đăng nhập")
        }
    }
}
```

- [ ] **Step 4: Home scaffold with 4 tabs**

`navigation/HomeScaffold.kt`:

```kotlin
package com.mykiot.pos.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.PointOfSale
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab(Routes.TAB_POS, "Bán", Icons.Filled.PointOfSale),
    Tab(Routes.TAB_RECEIPT, "Nhập", Icons.Filled.Receipt),
    Tab(Routes.TAB_INVENTORY, "Tồn", Icons.Filled.Inventory2),
    Tab(Routes.TAB_REPORT, "Báo cáo", Icons.Filled.Assessment),
)

@Composable
fun HomeScaffold(onLogout: () -> Unit) {
    var selected by remember { mutableStateOf(Routes.TAB_POS) }
    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = selected == tab.route,
                        onClick = { selected = tab.route },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
            val label = tabs.first { it.route == selected }.label
            Text("Màn '$label' — sẽ phát triển ở phase sau")
        }
    }
}
```

- [ ] **Step 5: AppNav (decides start destination from session)**

`navigation/AppNav.kt`:

```kotlin
package com.mykiot.pos.navigation

import androidx.compose.runtime.Composable
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.mykiot.pos.feature.auth.LoginScreen

@Composable
fun AppNav(startLoggedIn: Boolean) {
    val navController = rememberNavController()
    val start = if (startLoggedIn) Routes.HOME else Routes.LOGIN

    NavHost(navController = navController, startDestination = start) {
        composable(Routes.LOGIN) {
            LoginScreen(
                onLoggedIn = {
                    navController.navigate(Routes.HOME) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.HOME) {
            HomeScaffold(
                onLogout = {
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(Routes.HOME) { inclusive = true }
                    }
                },
            )
        }
    }
}
```

- [ ] **Step 6: Wire MainActivity to read session + theme**

Replace `MainActivity.kt` body:

```kotlin
package com.mykiot.pos

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Surface
import com.mykiot.pos.core.auth.TokenStore
import com.mykiot.pos.core.ui.theme.MyKiotTheme
import com.mykiot.pos.navigation.AppNav
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var tokenStore: TokenStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val loggedIn = tokenStore.hasSession()
        setContent {
            MyKiotTheme {
                Surface { AppNav(startLoggedIn = loggedIn) }
            }
        }
    }
}
```

- [ ] **Step 7: Build + manual smoke test**

Run: `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

Manual (emulator + backend running locally on `:8000`):
1. Start backend: `python -m uvicorn backend.main:app --reload --port 8000`.
2. Install app on emulator (`./gradlew :app:installDebug`), open it → Login screen in Vietnamese.
3. Register a shop via web/curl first, then log in with that phone/password → lands on Home with 4 tabs (Bán/Nhập/Tồn/Báo cáo).
4. Wrong password → Vietnamese error under the fields.
5. Kill & reopen app → still logged in (token persisted) → starts on Home.

Document the result of these 5 checks in the commit message or PR description.

- [ ] **Step 8: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/
git commit -m "feat(android): màn Đăng nhập (tiếng Việt) + shell 4 tab + auto-route theo phiên"
```

---

## Phase 1 Done — Definition of Done

- Backend: `/auth/mobile/login|refresh|logout` exist, tested (`tests/test_auth_mobile.py` green), web auth untouched/green.
- App: builds (`assembleDebug`), all JVM unit tests pass (`testDebugUnitTest`).
- A user can log in (incl. multi-tenant selection), session persists across restarts, 401s auto-refresh, all user-facing strings are Vietnamese.
- Foundation ready for Phase 2 (POS + hardware): networking, auth, DI, theme, navigation shell in place.

Next plan: **Phase 2 — Bán hàng (POS) + hardware (ML Kit scanner, súng HID, máy in ESC/POS 58mm)**, written after Phase 1 is implemented and reviewed.
