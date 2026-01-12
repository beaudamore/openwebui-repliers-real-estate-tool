"""
title: Repliers Listing Search Tool
author: beaudamore
version: 1.0.0
description: Search real estate listings via the Repliers API (POST /listings) with simple filters.
requirements: requests, pydantic
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field


def _clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of params without None or empty string values."""
    return {k: v for k, v in params.items() if v is not None and v != ""}


def _comma_join(value: Any) -> Any:
    """Convert lists/tuples to comma-separated strings; otherwise return as-is."""
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return value


def _split_city_state(city_or_district: Any, state: Any) -> (Any, Any):
    """If value looks like "City, ST", split into city and state."""
    if isinstance(city_or_district, str) and "," in city_or_district:
        parts = city_or_district.split(",", 1)
        city_clean = parts[0].strip()
        state_clean = parts[1].strip() if len(parts) > 1 else None
        return city_clean or city_or_district, state or state_clean
    return city_or_district, state



def _format_listings(listings: List[Dict[str, Any]]) -> str:
    """Build a detailed summary of all listings, leaving images as placeholders."""
    if not listings:
        return "No listings found."

    def _addr(addr: Dict[str, Any]) -> str:
        parts = [
            addr.get("streetNumber"),
            addr.get("streetName"),
            addr.get("streetSuffix"),
            addr.get("unitNumber"),
        ]
        line = " ".join(str(p) for p in parts if p).strip()
        city = addr.get("city")
        state = addr.get("state") or addr.get("province")
        postal = addr.get("postalCode") or addr.get("zip")
        tail = ", ".join(str(p) for p in [city, state, postal] if p)
        return ", ".join([c for c in [line, tail] if c]) or "Unknown address"

    lines: List[str] = []
    for idx, listing in enumerate(listings, start=1):
        address = listing.get("address") or {}
        details = listing.get("details") or {}
        condo = listing.get("condominium") or {}
        lot = listing.get("lot") or {}
        estimate = listing.get("estimate") or {}
        nearby = listing.get("nearby") or {}
        agents = listing.get("agents") or []

        price = listing.get("listPrice") or listing.get("price") or listing.get("list_price")
        beds = (
            details.get("numBedrooms")
            or listing.get("bedrooms")
            or listing.get("beds")
            or listing.get("bedroomsTotal")
        )
        baths = (
            details.get("numBathrooms")
            or listing.get("bathrooms")
            or listing.get("baths")
            or listing.get("bathroomsTotal")
        )
        sqft = details.get("sqft") or listing.get("sqft")
        year = details.get("yearBuilt") or listing.get("yearBuilt")
        status = listing.get("standardStatus") or listing.get("status")
        class_type = listing.get("class") or listing.get("propertyType")
        subtype = listing.get("type") or listing.get("style")
        dom = listing.get("simpleDaysOnMarket") or listing.get("daysOnMarket")
        hoa = details.get("HOAFee") or condo.get("fees", {}).get("maintenance")
        pets = condo.get("pets")
        amenities = nearby.get("amenities") or []
        lot_desc = lot.get("legalDescription") or lot.get("size")
        acres = lot.get("acres")
        coords = listing.get("map") or {}
        estimate_val = estimate.get("value")
        estimate_low = estimate.get("low")
        estimate_high = estimate.get("high")
        estimate_conf = estimate.get("confidence")
        brokerage = (listing.get("office") or {}).get("brokerageName")
        agent_names = ", ".join(a.get("name") for a in agents if a.get("name"))

        price_str = f"${price:,.0f}" if isinstance(price, (int, float)) else str(price or "N/A")
        sqft_str = f"{sqft}" if sqft is not None else "N/A"
        hoa_str = f"${hoa:,.0f}" if isinstance(hoa, (int, float)) else (str(hoa) if hoa else "N/A")
        estimate_str = (
            f"${estimate_val:,.0f} (range ${estimate_low:,.0f}-${estimate_high:,.0f}, conf {estimate_conf:.2f})"
            if isinstance(estimate_val, (int, float)) and isinstance(estimate_low, (int, float)) and isinstance(estimate_high, (int, float)) and isinstance(estimate_conf, (int, float))
            else (f"${estimate_val:,.0f}" if isinstance(estimate_val, (int, float)) else "N/A")
        )

        lines.append(
            "\n".join(
                [
                    f"{idx}. {listing.get('mlsNumber') or 'MLS N/A'} | status: {status or 'N/A'} | class/type: {class_type or 'N/A'} / {subtype or 'N/A'} | price: {price_str} | listDate: {listing.get('listDate') or 'N/A'} | DOM: {dom or 'N/A'}",
                    f"   Address: {_addr(address)} | neighborhood: {address.get('neighborhood') or 'N/A'}",
                    f"   Beds/Baths: {beds or 'N/A'}/{baths or 'N/A'} | sqft: {sqft_str} | year: {year or 'N/A'} | HOA: {hoa_str} | pets: {pets or 'N/A'}",
                    f"   Lot: {lot_desc or 'N/A'} | acres: {acres if acres is not None else 'N/A'}",
                    f"   Amenities: {', '.join(amenities) if amenities else 'N/A'}",
                    f"   Brokerage: {brokerage or 'N/A'} | Agents: {agent_names or 'N/A'}",
                    f"   Estimate: {estimate_str}",
                    f"   Map: lat {coords.get('latitude', 'N/A')}, long {coords.get('longitude', 'N/A')}",
                    f"   Images: [placeholder; photoCount={listing.get('photoCount', 'N/A')}]",
                ]
            )
        )

    return "\n".join(lines)


class Tools:
    class Valves(BaseModel):
        rapidapi_key: str = Field(
            default="",
            description="Repliers API key sent as REPLIERS-API-KEY header.",
        )
        base_url: str = Field(
            default="https://api.repliers.io",
            description="Base URL for the Repliers API.",
        )
        default_board_ids: Optional[str] = Field(
            default=None,
            description="Comma-separated board IDs to include in every request (optional).",
        )
        default_status: Optional[str] = Field(
            default="A",
            description="Listing status filter to apply when not provided (e.g., 'A').",
        )
        default_results_per_page: Optional[int] = Field(
            default=20,
            description="Number of listings to return per page when not provided.",
        )
        enable_debug_output: bool = Field(
            default=True,
            description="Include debug information in responses.",
        )

    def __init__(self):
        self.valves = self.Valves()

    @staticmethod
    async def emit_status(eventer, msg: str, done: bool = False, hidden: bool = False):
        await eventer({"type": "status", "data": {"description": msg, "done": done, "hidden": hidden}})

    @staticmethod
    async def emit_error(eventer, msg: str, done: bool = True, hidden: bool = False):
        await eventer({"type": "error", "data": {"description": msg, "done": done, "hidden": hidden}})

    @staticmethod
    async def emit_result(eventer, content: str, done: bool = True, hidden: bool = False):
        await eventer({"type": "result", "data": {"description": content, "done": done, "hidden": hidden}})

    async def search_listing(
        self,
        agent: Optional[Any] = None,
        aggregates: Optional[Any] = None,
        aggregateStatistics: Optional[Any] = None,
        amenities: Optional[Any] = None,
        amenitiesOperator: Optional[Any] = None,
        area: Optional[Any] = None,
        areaOrCity: Optional[Any] = None,
        balcony: Optional[Any] = None,
        basement: Optional[Any] = None,
        boardId: Optional[Any] = None,
        brokerage: Optional[Any] = None,
        businessSubType: Optional[Any] = None,
        businessType: Optional[Any] = None,
        city: Optional[Any] = None,
        cityOrDistrict: Optional[Any] = None,
        class_: Optional[Any] = None,
        cluster: Optional[Any] = None,
        clusterFields: Optional[Any] = None,
        clusterLimit: Optional[Any] = None,
        clusterPrecision: Optional[Any] = None,
        clusterStatistics: Optional[Any] = None,
        coverImage: Optional[Any] = None,
        den: Optional[Any] = None,
        displayAddressOnInternet: Optional[Any] = None,
        displayInternetEntireListing: Optional[Any] = None,
        displayPublic: Optional[Any] = None,
        district: Optional[Any] = None,
        driveway: Optional[Any] = None,
        exteriorConstruction: Optional[Any] = None,
        fields: Optional[Any] = None,
        garage: Optional[Any] = None,
        hasAgents: Optional[Any] = None,
        hasImages: Optional[Any] = None,
        heating: Optional[Any] = None,
        lastStatus: Optional[Any] = None,
        lat: Optional[Any] = None,
        listDate: Optional[Any] = None,
        listings: Optional[Any] = None,
        locker: Optional[Any] = None,
        long: Optional[Any] = None,
        map: Optional[Any] = None,  # noqa: A001  # pyright: ignore[reportShadowedBuiltin]
        mapOperator: Optional[Any] = None,
        maxBaths: Optional[Any] = None,
        maxBedrooms: Optional[Any] = None,
        maxBedroomsPlus: Optional[Any] = None,
        maxBedroomsTotal: Optional[Any] = None,
        maxKitchens: Optional[Any] = None,
        maxListDate: Optional[Any] = None,
        maxLotSizeSqft: Optional[Any] = None,
        maxMaintenanceFee: Optional[Any] = None,
        maxOpenHouseDate: Optional[Any] = None,
        maxParkingSpaces: Optional[Any] = None,
        maxPrice: Optional[Any] = None,
        maxRepliersUpdatedOn: Optional[Any] = None,
        maxSoldDate: Optional[Any] = None,
        maxSoldPrice: Optional[Any] = None,
        maxStreetNumber: Optional[Any] = None,
        maxSqft: Optional[Any] = None,
        maxTaxes: Optional[Any] = None,
        maxUnavailableDate: Optional[Any] = None,
        maxUpdatedOn: Optional[Any] = None,
        maxYearBuilt: Optional[Any] = None,
        minBaths: Optional[Any] = None,
        minBedrooms: Optional[Any] = None,
        minBedroomsPlus: Optional[Any] = None,
        minBedroomsTotal: Optional[Any] = None,
        minGarageSpaces: Optional[Any] = None,
        minKitchens: Optional[Any] = None,
        minListDate: Optional[Any] = None,
        minLotSizeSqft: Optional[Any] = None,
        minOpenHouseDate: Optional[Any] = None,
        minParkingSpaces: Optional[Any] = None,
        minPrice: Optional[Any] = None,
        minRepliersUpdatedOn: Optional[Any] = None,
        minSoldDate: Optional[Any] = None,
        minSoldPrice: Optional[Any] = None,
        minSqft: Optional[Any] = None,
        minStreetNumber: Optional[Any] = None,
        minTaxes: Optional[Any] = None,
        minUnavailableDate: Optional[Any] = None,
        minUpdatedOn: Optional[Any] = None,
        minYearBuilt: Optional[Any] = None,
        mlsNumber: Optional[Any] = None,
        neighborhood: Optional[Any] = None,
        officeId: Optional[Any] = None,
        operator: Optional[Any] = None,
        pageNum: Optional[Any] = None,
        propertyType: Optional[Any] = None,
        propertyTypeOrStyle: Optional[Any] = None,
        radius: Optional[Any] = None,
        resultsPerPage: Optional[Any] = None,
        search: Optional[Any] = None,
        searchFields: Optional[Any] = None,
        sortBy: Optional[Any] = None,
        sqft: Optional[Any] = None,
        statistics: Optional[Any] = None,
        standardStatus: Optional[Any] = None,
        status: Optional[Any] = None,
        streetDirection: Optional[Any] = None,
        streetName: Optional[Any] = None,
        streetNumber: Optional[Any] = None,
        streetSuffix: Optional[Any] = None,
        style: Optional[Any] = None,
        swimmingPool: Optional[Any] = None,
        type: Optional[Any] = None,  # noqa: A003  # pyright: ignore[reportShadowedBuiltin]
        unitNumber: Optional[Any] = None,
        updatedOn: Optional[Any] = None,
        waterSource: Optional[Any] = None,
        repliersUpdatedOn: Optional[Any] = None,
        sewer: Optional[Any] = None,
        state: Optional[Any] = None,
        waterfront: Optional[Any] = None,
        yearBuilt: Optional[Any] = None,
        zip: Optional[Any] = None,  # noqa: A002  # pyright: ignore[reportShadowedBuiltin]
        zoning: Optional[Any] = None,
        __event_emitter__=None,
    ) -> str:
        """
        Search listings via Repliers POST /listings. The LLM should set the `rapidapi_key` valve before calling.

        Common parameters (exactly as the Repliers Postman collection defines). IMPORTANT FOR LLM USE:
        - Put city name in `city` or `cityOrDistrict` without state.
        - Put the state/province code in `state` (e.g., FL, ON). Do not append state to city fields.
                - Arrays are supported by passing Python lists (e.g., status=["A","U"]).
                - The request body stays empty (image search is not used).
                - Optional defaults from valves: if provided, `default_board_ids`, `default_status`, and
                    `default_results_per_page` are applied when the corresponding parameters are missing.

        All parameters:
        agent, aggregates, aggregateStatistics, amenities, amenitiesOperator, area, areaOrCity, balcony, basement,
        boardId, brokerage, businessSubType, businessType, city, cityOrDistrict, class, cluster, clusterFields,
        clusterLimit, clusterPrecision, clusterStatistics, coverImage, den, displayAddressOnInternet,
        displayInternetEntireListing, displayPublic, district, driveway, exteriorConstruction, fields, garage,
        hasAgents, hasImages, heating, lastStatus, lat, listDate, listings, locker, long, map, mapOperator,
        maxBaths, maxBedrooms, maxBedroomsPlus, maxBedroomsTotal, maxKitchens, maxListDate, maxLotSizeSqft,
        maxMaintenanceFee, maxOpenHouseDate, maxParkingSpaces, maxPrice, maxRepliersUpdatedOn, maxSoldDate,
        maxSoldPrice, maxStreetNumber, maxSqft, maxTaxes, maxUnavailableDate, maxUpdatedOn, maxYearBuilt,
        minBaths, minBedrooms, minBedroomsPlus, minBedroomsTotal, minGarageSpaces, minKitchens, minListDate,
        minLotSizeSqft, minOpenHouseDate, minParkingSpaces, minPrice, minRepliersUpdatedOn, minSoldDate,
        minSoldPrice, minSqft, minStreetNumber, minTaxes, minUnavailableDate, minUpdatedOn, minYearBuilt,
        mlsNumber, neighborhood, officeId, operator, pageNum, propertyType, propertyTypeOrStyle, radius,
        resultsPerPage, search, searchFields, sortBy, sqft, statistics, standardStatus, status, streetDirection,
        streetName, streetNumber, streetSuffix, style, swimmingPool, type, unitNumber, updatedOn, waterSource,
        repliersUpdatedOn, sewer, state, waterfront, yearBuilt, zip, zoning.

        - No defaults are injected. Only provided parameters are sent.

        Output: emits a brief text summary of the first few listings (address, price, beds, baths) and optional debug info.
        """

        eventer = __event_emitter__ or (lambda *args, **kwargs: asyncio.sleep(0))

        if not self.valves.rapidapi_key:
            msg = "rapidapi_key valve is empty; set your Repliers API key first."
            await self.emit_error(eventer, msg)
            return msg

        headers = {
            "REPLIERS-API-KEY": self.valves.rapidapi_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        city, state = _split_city_state(city, state)
        cityOrDistrict, state = _split_city_state(cityOrDistrict, state)
        areaOrCity, state = _split_city_state(areaOrCity, state)

        entry_debug = ""
        if self.valves.enable_debug_output:
            entry_debug = json.dumps(
                {
                    "raw_city": city,
                    "raw_areaOrCity": areaOrCity,
                    "raw_cityOrDistrict": cityOrDistrict,
                    "raw_state": state,
                },
                indent=2,
            )

        params: Dict[str, Any] = {
            "agent": agent,
            "aggregates": aggregates,
            "aggregateStatistics": aggregateStatistics,
            "amenities": amenities,
            "amenitiesOperator": amenitiesOperator,
            "area": area,
            "areaOrCity": areaOrCity,
            "balcony": balcony,
            "basement": basement,
            "boardId": boardId,
            "brokerage": brokerage,
            "businessSubType": businessSubType,
            "businessType": businessType,
            "city": city,
            "cityOrDistrict": cityOrDistrict,
            "class": class_,
            "cluster": cluster,
            "clusterFields": clusterFields,
            "clusterLimit": clusterLimit,
            "clusterPrecision": clusterPrecision,
            "clusterStatistics": clusterStatistics,
            "coverImage": coverImage,
            "den": den,
            "displayAddressOnInternet": displayAddressOnInternet,
            "displayInternetEntireListing": displayInternetEntireListing,
            "displayPublic": displayPublic,
            "district": district,
            "driveway": driveway,
            "exteriorConstruction": exteriorConstruction,
            "fields": _comma_join(fields),
            "garage": garage,
            "hasAgents": hasAgents,
            "hasImages": hasImages,
            "heating": heating,
            "lastStatus": lastStatus,
            "lat": lat,
            "listDate": listDate,
            "listings": listings,
            "locker": locker,
            "long": long,
            "map": map,
            "mapOperator": mapOperator,
            "maxBaths": maxBaths,
            "maxBedrooms": maxBedrooms,
            "maxBedroomsPlus": maxBedroomsPlus,
            "maxBedroomsTotal": maxBedroomsTotal,
            "maxKitchens": maxKitchens,
            "maxListDate": maxListDate,
            "maxLotSizeSqft": maxLotSizeSqft,
            "maxMaintenanceFee": maxMaintenanceFee,
            "maxOpenHouseDate": maxOpenHouseDate,
            "maxParkingSpaces": maxParkingSpaces,
            "maxPrice": maxPrice,
            "maxRepliersUpdatedOn": maxRepliersUpdatedOn,
            "maxSoldDate": maxSoldDate,
            "maxSoldPrice": maxSoldPrice,
            "maxStreetNumber": maxStreetNumber,
            "maxSqft": maxSqft,
            "maxTaxes": maxTaxes,
            "maxUnavailableDate": maxUnavailableDate,
            "maxUpdatedOn": maxUpdatedOn,
            "maxYearBuilt": maxYearBuilt,
            "minBaths": minBaths,
            "minBedrooms": minBedrooms,
            "minBedroomsPlus": minBedroomsPlus,
            "minBedroomsTotal": minBedroomsTotal,
            "minGarageSpaces": minGarageSpaces,
            "minKitchens": minKitchens,
            "minListDate": minListDate,
            "minLotSizeSqft": minLotSizeSqft,
            "minOpenHouseDate": minOpenHouseDate,
            "minParkingSpaces": minParkingSpaces,
            "minPrice": minPrice,
            "minRepliersUpdatedOn": minRepliersUpdatedOn,
            "minSoldDate": minSoldDate,
            "minSoldPrice": minSoldPrice,
            "minSqft": minSqft,
            "minStreetNumber": minStreetNumber,
            "minTaxes": minTaxes,
            "minUnavailableDate": minUnavailableDate,
            "minUpdatedOn": minUpdatedOn,
            "minYearBuilt": minYearBuilt,
            "mlsNumber": mlsNumber,
            "neighborhood": neighborhood,
            "officeId": officeId,
            "operator": operator,
            "pageNum": pageNum,
            "propertyType": propertyType,
            "propertyTypeOrStyle": propertyTypeOrStyle,
            "radius": radius,
            "resultsPerPage": resultsPerPage,
            "search": search,
            "searchFields": _comma_join(searchFields),
            "sortBy": sortBy,
            "sqft": sqft,
            "statistics": statistics,
            "standardStatus": standardStatus,
            "status": status,
            "streetDirection": streetDirection,
            "streetName": streetName,
            "streetNumber": streetNumber,
            "streetSuffix": streetSuffix,
            "style": style,
            "swimmingPool": swimmingPool,
            "type": type,
            "unitNumber": unitNumber,
            "updatedOn": updatedOn,
            "waterSource": waterSource,
            "repliersUpdatedOn": repliersUpdatedOn,
            "sewer": sewer,
            "state": state,
            "waterfront": waterfront,
            "yearBuilt": yearBuilt,
            "zip": zip,
            "zoning": zoning,
        }

        if not params.get("boardId") and self.valves.default_board_ids:
            params["boardId"] = self.valves.default_board_ids
        if params.get("status") is None and self.valves.default_status:
            params["status"] = self.valves.default_status
        if params.get("resultsPerPage") is None and self.valves.default_results_per_page:
            params["resultsPerPage"] = self.valves.default_results_per_page

        params = _clean_params(params)

        url = f"{self.valves.base_url}/listings"
        payload: Dict[str, Any] = {}

        debug = ""
        if self.valves.enable_debug_output:
            debug = json.dumps({"url": url, "params": params, "entry": entry_debug}, indent=2)

        await self.emit_status(eventer, "Sending listing search request...")

        try:
            def _do_request():
                return requests.post(url, params=params, json=payload, headers=headers, timeout=30)

            response = await asyncio.get_event_loop().run_in_executor(None, _do_request)
            response.raise_for_status()

            data = response.json()
            listings = data.get("listings") or data.get("results") or data.get("items") or []
            if not isinstance(listings, list):
                listings = []
            summary = _format_listings(listings)
            full_json = json.dumps(data, indent=2)
            output = f"Listing search complete.\n{summary}\n\nFull response JSON:\n{full_json}"
            if debug:
                output = f"Debug:\n{debug}\n\n" + output

            await self.emit_result(eventer, output)
            await self.emit_status(eventer, "Done", done=True)
            return output

        except requests.HTTPError as exc:
            msg = f"HTTP error {exc.response.status_code}: {exc.response.text}"
            await self.emit_error(eventer, msg)
            return msg
        except requests.RequestException as exc:
            msg = f"Request failed: {exc}"
            await self.emit_error(eventer, msg)
            return msg
        except ValueError as exc:
            msg = f"Failed to parse response JSON: {exc}"
            await self.emit_error(eventer, msg)
            return msg
        except Exception as exc:  # noqa: BLE001
            msg = f"Unexpected error: {exc}"
            await self.emit_error(eventer, msg)
            return msg
