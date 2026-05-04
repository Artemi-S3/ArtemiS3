/**
 * Geospatial preview parsing pipeline.
 * Converts GeoJSON/KML/KMZ inputs into normalized GeoJSON for map rendering.
 */
import JSZip from "jszip";
import { kml as convertKmlToGeoJson } from "@tmcw/togeojson";
import {
  GEOSPATIAL_SIZE_CAP_BYTES,
  SUPPORTED_GEOSPATIAL_EXTENSIONS,
  type GeospatialFormat,
  type GeospatialPreviewResult,
  type GeoJsonFeature,
  type GeoJsonFeatureCollection,
  type GeoJsonGeometry,
  type GeoJsonGeometryType,
} from "../schemas/geospatial";

const GEOMETRY_TYPES = new Set<GeoJsonGeometryType>([
  "Point",
  "MultiPoint",
  "LineString",
  "MultiLineString",
  "Polygon",
  "MultiPolygon",
  "GeometryCollection",
]);

/** Error categories returned from preview loading/parsing operations. */
type GeospatialPreviewErrorCode =
  | "unsupported_format"
  | "size_limit"
  | "network"
  | "parse";

/** Input payload required to load and parse a preview document. */
type GeospatialPreviewInput = {
  key: string;
  size: number;
  previewUrl: string;
};

/** Domain-specific error used by geospatial preview helpers. */
export class GeospatialPreviewError extends Error {
  code: GeospatialPreviewErrorCode;

  constructor(code: GeospatialPreviewErrorCode, message: string) {
    super(message);
    this.code = code;
    this.name = "GeospatialPreviewError";
  }
}

/** Guards unknown values as non-null object records. */
function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

/** Validates that an unknown value matches supported GeoJSON geometry shape. */
function isGeometry(value: unknown): value is GeoJsonGeometry {
  if (!isRecord(value)) return false;
  if (typeof value.type !== "string") return false;
  if (!GEOMETRY_TYPES.has(value.type as GeoJsonGeometryType)) return false;

  if (value.type === "GeometryCollection") {
    if (!Array.isArray(value.geometries)) return false;
    return value.geometries.every(isGeometry);
  }

  return "coordinates" in value;
}

/** Normalizes a raw GeoJSON feature into the frontend's strict feature model. */
function normalizeFeature(feature: unknown): GeoJsonFeature {
  if (!isRecord(feature) || feature.type !== "Feature") {
    throw new GeospatialPreviewError(
      "parse",
      "Unsupported GeoJSON feature structure. Download this file instead.",
    );
  }

  const geometry = feature.geometry ?? null;
  if (geometry !== null && !isGeometry(geometry)) {
    throw new GeospatialPreviewError(
      "parse",
      "Invalid geometry in geospatial file. Download this file instead.",
    );
  }

  const properties =
    feature.properties === undefined || feature.properties === null
      ? null
      : isRecord(feature.properties)
        ? feature.properties
        : null;

  const normalized: GeoJsonFeature = {
    type: "Feature",
    geometry,
    properties,
  };

  if (typeof feature.id === "string" || typeof feature.id === "number") {
    normalized.id = feature.id;
  }

  return normalized;
}

/** Normalizes raw GeoJSON/geometry payloads into a FeatureCollection wrapper. */
export function normalizeGeoJsonInput(raw: unknown): GeoJsonFeatureCollection {
  if (!isRecord(raw) || typeof raw.type !== "string") {
    throw new GeospatialPreviewError(
      "parse",
      "Unsupported geospatial content. Download this file instead.",
    );
  }

  if (raw.type === "FeatureCollection") {
    if (!Array.isArray(raw.features)) {
      throw new GeospatialPreviewError(
        "parse",
        "GeoJSON FeatureCollection is missing features. Download this file instead.",
      );
    }
    return {
      type: "FeatureCollection",
      features: raw.features.map(normalizeFeature),
    };
  }

  if (raw.type === "Feature") {
    return {
      type: "FeatureCollection",
      features: [normalizeFeature(raw)],
    };
  }

  if (isGeometry(raw)) {
    return {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: raw,
          properties: null,
        },
      ],
    };
  }

  throw new GeospatialPreviewError(
    "parse",
    "Unsupported GeoJSON structure. Download this file instead.",
  );
}

/** Collects geometry types recursively, including nested collections. */
function collectGeometryTypes(
  geometry: GeoJsonGeometry | null,
  collector: Set<GeoJsonGeometryType>,
): void {
  if (!geometry) return;
  collector.add(geometry.type);

  if (geometry.type === "GeometryCollection" && geometry.geometries) {
    geometry.geometries.forEach((nested) => collectGeometryTypes(nested, collector));
  }
}

/** Computes feature and geometry-type metadata for preview summaries. */
function metadataFromFeatureCollection(
  featureCollection: GeoJsonFeatureCollection,
): Pick<GeospatialPreviewResult, "featureCount" | "geometryTypes"> {
  const geometryTypes = new Set<GeoJsonGeometryType>();
  featureCollection.features.forEach((feature) => {
    collectGeometryTypes(feature.geometry, geometryTypes);
  });
  return {
    featureCount: featureCollection.features.length,
    geometryTypes: [...geometryTypes],
  };
}

type CoordinateStats = {
  total: number;
  normalValid: number;
  swappedValid: number;
  lonGt180: number;
  lonNegative: number;
};

/** Checks whether value is a finite number. */
function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Walks recursively through coordinate arrays and visits lon/lat pairs. */
function visitCoordinatePairs(
  value: unknown,
  visitor: (lon: number, lat: number, rest: number[]) => void,
): void {
  if (!Array.isArray(value)) return;

  if (
    value.length >= 2 &&
    isFiniteNumber(value[0]) &&
    isFiniteNumber(value[1])
  ) {
    const lon = value[0];
    const lat = value[1];
    const rest = value
      .slice(2)
      .filter((entry): entry is number => isFiniteNumber(entry));
    visitor(lon, lat, rest);
    return;
  }

  value.forEach((entry) => visitCoordinatePairs(entry, visitor));
}

/** Maps recursively through coordinate arrays and rewrites lon/lat pairs. */
function mapCoordinatePairs(
  value: unknown,
  mapper: (lon: number, lat: number, rest: number[]) => number[],
): unknown {
  if (!Array.isArray(value)) return value;

  if (
    value.length >= 2 &&
    isFiniteNumber(value[0]) &&
    isFiniteNumber(value[1])
  ) {
    const lon = value[0];
    const lat = value[1];
    const rest = value
      .slice(2)
      .filter((entry): entry is number => isFiniteNumber(entry));
    return mapper(lon, lat, rest);
  }

  return value.map((entry) => mapCoordinatePairs(entry, mapper));
}

/** Applies coordinate mapping to one geometry tree. */
function mapGeometryCoordinates(
  geometry: GeoJsonGeometry | null,
  mapper: (lon: number, lat: number, rest: number[]) => number[],
): GeoJsonGeometry | null {
  if (!geometry) return geometry;
  if (geometry.type === "GeometryCollection" && geometry.geometries) {
    return {
      ...geometry,
      geometries: geometry.geometries.map((nested) =>
        mapGeometryCoordinates(nested, mapper),
      ) as GeoJsonGeometry[],
    };
  }

  if (!("coordinates" in geometry)) return geometry;
  return {
    ...geometry,
    coordinates: mapCoordinatePairs(geometry.coordinates, mapper),
  };
}

/** Applies coordinate mapping to every feature in a collection. */
function mapFeatureCollectionCoordinates(
  featureCollection: GeoJsonFeatureCollection,
  mapper: (lon: number, lat: number, rest: number[]) => number[],
): GeoJsonFeatureCollection {
  return {
    type: "FeatureCollection",
    features: featureCollection.features.map((feature) => ({
      ...feature,
      geometry: mapGeometryCoordinates(feature.geometry, mapper),
    })),
  };
}

/** Collects coordinate validity metrics for normalization heuristics. */
function collectCoordinateStats(featureCollection: GeoJsonFeatureCollection): CoordinateStats {
  const stats: CoordinateStats = {
    total: 0,
    normalValid: 0,
    swappedValid: 0,
    lonGt180: 0,
    lonNegative: 0,
  };

  featureCollection.features.forEach((feature) => {
    const geometry = feature.geometry;
    if (!geometry) return;

    if (geometry.type === "GeometryCollection" && geometry.geometries) {
      geometry.geometries.forEach((nested) => {
        if (!nested || !("coordinates" in nested)) return;
        visitCoordinatePairs(nested.coordinates, (lon, lat) => {
          stats.total += 1;
          if (Math.abs(lon) <= 180 && Math.abs(lat) <= 90) {
            stats.normalValid += 1;
          }
          if (Math.abs(lat) <= 180 && Math.abs(lon) <= 90) {
            stats.swappedValid += 1;
          }
          if (lon > 180) stats.lonGt180 += 1;
          if (lon < 0) stats.lonNegative += 1;
        });
      });
      return;
    }

    if (!("coordinates" in geometry)) return;
    visitCoordinatePairs(geometry.coordinates, (lon, lat) => {
      stats.total += 1;
      if (Math.abs(lon) <= 180 && Math.abs(lat) <= 90) {
        stats.normalValid += 1;
      }
      if (Math.abs(lat) <= 180 && Math.abs(lon) <= 90) {
        stats.swappedValid += 1;
      }
      if (lon > 180) stats.lonGt180 += 1;
      if (lon < 0) stats.lonNegative += 1;
    });
  });

  return stats;
}

/** Normalizes coordinate ordering/ranges and emits normalization metadata. */
function normalizeFeatureCollectionCoordinates(featureCollection: GeoJsonFeatureCollection): {
  featureCollection: GeoJsonFeatureCollection;
  normalization: GeospatialPreviewResult["normalization"];
} {
  let normalized = featureCollection;
  let swappedCoordinateOrder = false;
  let wrappedLongitudes = false;

  const initialStats = collectCoordinateStats(normalized);
  if (initialStats.total === 0) {
    return {
      featureCollection: normalized,
      normalization: {
        swappedCoordinateOrder: false,
        wrappedLongitudes: false,
        coordinatePairs: 0,
        validCoordinateRatio: 1,
      },
    };
  }

  const normalRatio = initialStats.normalValid / initialStats.total;
  const swappedRatio = initialStats.swappedValid / initialStats.total;

  // Some KML/KMZ files are encoded as lat,lon instead of lon,lat.
  if (swappedRatio >= 0.85 && swappedRatio > normalRatio + 0.25) {
    swappedCoordinateOrder = true;
    normalized = mapFeatureCollectionCoordinates(normalized, (lon, lat, rest) => [
      lat,
      lon,
      ...rest,
    ]);
  }

  const afterSwapStats = collectCoordinateStats(normalized);
  const lonGt180Ratio =
    afterSwapStats.total > 0 ? afterSwapStats.lonGt180 / afterSwapStats.total : 0;
  const hasMostlyPositiveLongitudes =
    afterSwapStats.total > 0 &&
    afterSwapStats.lonNegative / afterSwapStats.total <= 0.02;

  // Planetary products often use 0..360 longitudes. Wrap to -180..180 for display.
  if (lonGt180Ratio >= 0.25 && hasMostlyPositiveLongitudes) {
    wrappedLongitudes = true;
    normalized = mapFeatureCollectionCoordinates(normalized, (lon, lat, rest) => [
      lon > 180 ? lon - 360 : lon,
      lat,
      ...rest,
    ]);
  }

  const finalStats = collectCoordinateStats(normalized);
  const validCoordinateRatio =
    finalStats.total > 0 ? finalStats.normalValid / finalStats.total : 1;
  if (finalStats.total > 0 && validCoordinateRatio < 0.75) {
    throw new GeospatialPreviewError(
      "parse",
      "Coordinates appear to use an unsupported reference system for this map preview. Download this file instead.",
    );
  }

  return {
    featureCollection: normalized,
    normalization: {
      swappedCoordinateOrder,
      wrappedLongitudes,
      coordinatePairs: finalStats.total,
      validCoordinateRatio,
    },
  };
}

/** Formats bytes for user-facing size-limit messages. */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

/** Parses GeoJSON text and normalizes its shape. */
function parseGeoJsonText(text: string): GeoJsonFeatureCollection {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new GeospatialPreviewError(
      "parse",
      "Malformed GeoJSON file. Download this file instead.",
    );
  }
  return normalizeGeoJsonInput(parsed);
}

/** Parses KML XML text and converts it into normalized GeoJSON. */
function parseKmlText(text: string): GeoJsonFeatureCollection {
  let xmlDocument: Document;
  try {
    xmlDocument = new DOMParser().parseFromString(text, "application/xml");
  } catch {
    throw new GeospatialPreviewError(
      "parse",
      "Malformed KML file. Download this file instead.",
    );
  }

  if (xmlDocument.querySelector("parsererror")) {
    throw new GeospatialPreviewError(
      "parse",
      "Malformed KML file. Download this file instead.",
    );
  }

  const asGeoJson = convertKmlToGeoJson(xmlDocument);
  return normalizeGeoJsonInput(asGeoJson);
}

/** Parses KMZ archive bytes and extracts the first embedded KML document. */
async function parseKmzBuffer(buffer: ArrayBuffer): Promise<GeoJsonFeatureCollection> {
  let zip: JSZip;
  try {
    zip = await JSZip.loadAsync(buffer);
  } catch {
    throw new GeospatialPreviewError(
      "parse",
      "Malformed KMZ archive. Download this file instead.",
    );
  }

  const kmlEntry = Object.values(zip.files).find(
    (entry) => !entry.dir && entry.name.toLowerCase().endsWith(".kml"),
  );
  if (!kmlEntry) {
    throw new GeospatialPreviewError(
      "parse",
      "KMZ file has no embedded KML document. Download this file instead.",
    );
  }

  const kmlText = await kmlEntry.async("text");
  return parseKmlText(kmlText);
}

/** Fetches preview content and maps network failures into domain errors. */
async function fetchPreview(previewUrl: string): Promise<Response> {
  try {
    return await fetch(previewUrl);
  } catch {
    throw new GeospatialPreviewError(
      "network",
      "Could not fetch geospatial preview from S3. Download this file instead.",
    );
  }
}

/** Infers geospatial format from key extension. */
export function getGeospatialFormatFromKey(key: string): GeospatialFormat | null {
  const normalizedKey = key.trim().toLowerCase().split("?")[0];
  if (normalizedKey.endsWith(".geojson")) return "geojson";
  if (normalizedKey.endsWith(".kml")) return "kml";
  if (normalizedKey.endsWith(".kmz")) return "kmz";
  return null;
}

/** Indicates whether a key can be parsed by the geospatial preview pipeline. */
export function isGeospatialPreviewableKey(key: string): boolean {
  return getGeospatialFormatFromKey(key) !== null;
}

/** Returns supported geospatial extensions for UI usage. */
export function getGeospatialExtensions(): readonly string[] {
  return SUPPORTED_GEOSPATIAL_EXTENSIONS;
}

/** Loads, parses, and normalizes geospatial preview data from an S3 preview URL. */
export async function loadGeospatialPreviewFromUrl(
  input: GeospatialPreviewInput,
): Promise<GeospatialPreviewResult> {
  const format = getGeospatialFormatFromKey(input.key);
  if (!format) {
    throw new GeospatialPreviewError(
      "unsupported_format",
      "This file format is not supported for map preview.",
    );
  }

  if (input.size > GEOSPATIAL_SIZE_CAP_BYTES) {
    throw new GeospatialPreviewError(
      "size_limit",
      `This geospatial file is ${formatBytes(input.size)} and exceeds the 15 MB preview limit. Download this file instead.`,
    );
  }

  const response = await fetchPreview(input.previewUrl);
  if (!response.ok) {
    throw new GeospatialPreviewError(
      "network",
      `Could not fetch geospatial preview (${response.status}). Download this file instead.`,
    );
  }

  let featureCollection: GeoJsonFeatureCollection;
  let normalizedResult: ReturnType<typeof normalizeFeatureCollectionCoordinates>;
  try {
    if (format === "geojson") {
      featureCollection = parseGeoJsonText(await response.text());
    } else if (format === "kml") {
      featureCollection = parseKmlText(await response.text());
    } else {
      featureCollection = await parseKmzBuffer(await response.arrayBuffer());
    }
    normalizedResult = normalizeFeatureCollectionCoordinates(featureCollection);
  } catch (error) {
    if (error instanceof GeospatialPreviewError) {
      throw error;
    }
    throw new GeospatialPreviewError(
      "parse",
      "Failed to parse geospatial file. Download this file instead.",
    );
  }

  if (featureCollection.features.length === 0) {
    throw new GeospatialPreviewError(
      "parse",
      "This geospatial file has no features to display. Download this file instead.",
    );
  }

  return {
    format,
    featureCollection: normalizedResult.featureCollection,
    ...metadataFromFeatureCollection(normalizedResult.featureCollection),
    normalization: normalizedResult.normalization,
  };
}
