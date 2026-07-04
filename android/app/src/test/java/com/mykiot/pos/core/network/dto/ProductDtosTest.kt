package com.mykiot.pos.core.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertTrue
import org.junit.Test

class ProductDtosTest {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    @Test
    fun `ProductUpdateDto serializes default-valued fields explicitly`() {
        val dto = ProductUpdateDto(
            name = "Coca",
            unit = "cái",
            salePrice = "12000",
            minStock = 0,
            status = "ACTIVE",
        )
        val encoded = json.encodeToString(ProductUpdateDto.serializer(), dto)
        assertTrue("expected status in $encoded", encoded.contains("\"status\":\"ACTIVE\""))
        assertTrue("expected min_stock in $encoded", encoded.contains("\"min_stock\":0"))
        assertTrue("expected unit in $encoded", encoded.contains("\"unit\":\"cái\""))
    }

    @Test
    fun `ProductUpdateDto costPrice null is sent explicitly with encodeDefaults true`() {
        // With encodeDefaults = true, kotlinx.serialization no longer skips fields that
        // equal their declared default (null, for costPrice). Since Json's `explicitNulls`
        // defaults to true, the null is now serialized explicitly as "cost_price":null
        // instead of being omitted from the body entirely.
        //
        // This does NOT reintroduce the class of bug this DTO's costPrice=null was designed
        // to avoid (accidentally overwriting cost_price when Cashier's form hides the field):
        // backend/modules/product/service.py::update_product only writes a field when both
        // (a) the key is present in the JSON body (payload.model_dump(exclude_unset=True))
        // AND (b) its value is not None. An explicit `"cost_price": null` satisfies (a) but
        // fails (b), so the field is still left untouched — same effective behavior as before,
        // just via an explicit null rather than a missing key.
        val dto = ProductUpdateDto(name = "Coca", costPrice = null)
        val encoded = json.encodeToString(ProductUpdateDto.serializer(), dto)
        assertTrue("expected explicit null cost_price in $encoded", encoded.contains("\"cost_price\":null"))
    }
}
