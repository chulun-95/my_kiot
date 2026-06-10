package com.mykiot.pos.core.network

/** A failure already translated to a user-facing Vietnamese message. */
data class ApiError(
    val code: String,
    val message: String,
    val httpStatus: Int? = null,
)
