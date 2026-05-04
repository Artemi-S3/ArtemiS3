/**
 * Utilities that reduce geospatial render load for Leaflet previews.
 * Applies grouping, down-sampling, and coordinate simplification.
 */
import type {
  GeoJsonFeature,
  GeoJsonFeatureCollection,
  GeoJsonGeometry,
} from "../schemas/geospatial";

const MAX_POINT_FEATURES = 12000;
const MAX_LINE_LIKE_FEATURES = 3500;
const MAX_COORDS_PER_LINESTRING = 220;
const MAX_COORDS_PER_RING = 220;

/** Precomputed render-ready collections and sampling metadata. */
export type GeospatialRenderPreparation = {
  pointCollection: GeoJsonFeatureCollection;
  lineCollection: GeoJsonFeatureCollection;
  sourceFeatureCount: number;
  sourcePointFeatures: number;
  sourceLineFeatures: number;
  sourcePolygonFeatures: number;
  renderedPointFeatures: number;
  renderedLineFeatures: number;
  sampledPoints: boolean;
  sampledLines: boolean;
  simplifiedGeometries: number;
};

/** Worker/main-thread message format for render preparation results. */
export type GeospatialRenderPrepMessage =
  | {
    ok: true;
    data: GeospatialRenderPreparation;
  }
  | {
    ok: false;
    error: string;
  };

type GeometryGroup = "point" | "line_like" | "unknown";

/** Buckets geometry types into point-like vs line/polygon-like groups. */
function groupGeometry(geometry: GeoJsonGeometry | null): GeometryGroup {
  if (!geometry) return "unknown";

  if (geometry.type === "Point" || geometry.type === "MultiPoint") {
    return "point";
  }

  if (
    geometry.type === "LineString" ||
    geometry.type === "MultiLineString" ||
    geometry.type === "Polygon" ||
    geometry.type === "MultiPolygon" ||
    geometry.type === "GeometryCollection"
  ) {
    return "line_like";
  }

  return "unknown";
}

/** Down-samples an array by stride so it does not exceed a fixed maximum. */
function decimateByStride<T>(items: T[], maxItems: number): { items: T[]; sampled: boolean } {
  if (items.length <= maxItems) {
    return { items, sampled: false };
  }

  const step = Math.ceil(items.length / maxItems);
  const sampled = items.filter((_item, index) => index % step === 0).slice(0, maxItems);
  return { items: sampled, sampled: true };
}

/** Recursively decimates coordinate pair arrays while preserving nesting shape. */
function decimatePairs(coords: unknown, maxPairs: number): unknown {
  if (!Array.isArray(coords)) return coords;

  if (
    coords.length >= 2 &&
    typeof coords[0] === "number" &&
    typeof coords[1] === "number"
  ) {
    return coords;
  }

  const looksLikePairArray =
    coords.length > 0 &&
    Array.isArray(coords[0]) &&
    (coords[0] as unknown[]).length >= 2 &&
    typeof (coords[0] as unknown[])[0] === "number" &&
    typeof (coords[0] as unknown[])[1] === "number";

  if (looksLikePairArray) {
    const pairArray = coords as unknown[];
    if (pairArray.length <= maxPairs) return pairArray;
    const step = Math.ceil(pairArray.length / maxPairs);
    return pairArray.filter((_item, index) => index % step === 0).slice(0, maxPairs);
  }

  return coords.map((entry) => decimatePairs(entry, maxPairs));
}

/** Simplifies a single geometry's coordinate density when needed. */
function simplifyGeometry(geometry: GeoJsonGeometry | null): {
  geometry: GeoJsonGeometry | null;
  simplified: boolean;
} {
  if (!geometry) {
    return { geometry, simplified: false };
  }

  if (geometry.type === "GeometryCollection") {
    const simplifiedChildren = (geometry.geometries ?? []).map((child) =>
      simplifyGeometry(child),
    );
    return {
      geometry: {
        ...geometry,
        geometries: simplifiedChildren.map((entry) => entry.geometry as GeoJsonGeometry),
      },
      simplified: simplifiedChildren.some((entry) => entry.simplified),
    };
  }

  if (!("coordinates" in geometry)) {
    return { geometry, simplified: false };
  }

  let nextCoordinates = geometry.coordinates;
  let simplified = false;

  if (geometry.type === "LineString" || geometry.type === "MultiLineString") {
    nextCoordinates = decimatePairs(geometry.coordinates, MAX_COORDS_PER_LINESTRING);
    simplified = nextCoordinates !== geometry.coordinates;
  } else if (geometry.type === "Polygon" || geometry.type === "MultiPolygon") {
    nextCoordinates = decimatePairs(geometry.coordinates, MAX_COORDS_PER_RING);
    simplified = nextCoordinates !== geometry.coordinates;
  }

  return {
    geometry: {
      ...geometry,
      coordinates: nextCoordinates,
    },
    simplified,
  };
}

/** Simplifies one feature while preserving non-geometry attributes. */
function simplifyFeature(feature: GeoJsonFeature): {
  feature: GeoJsonFeature;
  simplified: boolean;
} {
  const simplifiedGeometry = simplifyGeometry(feature.geometry);
  return {
    feature: {
      ...feature,
      geometry: simplifiedGeometry.geometry,
    },
    simplified: simplifiedGeometry.simplified,
  };
}

/** Splits feature collection into point and line-like layers, then samples for rendering. */
export function prepareFeatureCollectionForRendering(
  featureCollection: GeoJsonFeatureCollection,
): GeospatialRenderPreparation {
  const pointFeatures: GeoJsonFeature[] = [];
  const lineLikeFeatures: GeoJsonFeature[] = [];
  let sourcePointFeatures = 0;
  let sourceLineFeatures = 0;
  let sourcePolygonFeatures = 0;
  let simplifiedGeometries = 0;

  featureCollection.features.forEach((feature) => {
    const group = groupGeometry(feature.geometry);

    if (feature.geometry?.type === "Point" || feature.geometry?.type === "MultiPoint") {
      sourcePointFeatures += 1;
    } else if (
      feature.geometry?.type === "LineString" ||
      feature.geometry?.type === "MultiLineString"
    ) {
      sourceLineFeatures += 1;
    } else if (
      feature.geometry?.type === "Polygon" ||
      feature.geometry?.type === "MultiPolygon"
    ) {
      sourcePolygonFeatures += 1;
    }

    if (group === "point") {
      pointFeatures.push(feature);
      return;
    }

    if (group === "line_like") {
      const simplified = simplifyFeature(feature);
      if (simplified.simplified) {
        simplifiedGeometries += 1;
      }
      lineLikeFeatures.push(simplified.feature);
    }
  });

  const sampledPoints = decimateByStride(pointFeatures, MAX_POINT_FEATURES);
  const sampledLines = decimateByStride(lineLikeFeatures, MAX_LINE_LIKE_FEATURES);

  return {
    pointCollection: {
      type: "FeatureCollection",
      features: sampledPoints.items,
    },
    lineCollection: {
      type: "FeatureCollection",
      features: sampledLines.items,
    },
    sourceFeatureCount: featureCollection.features.length,
    sourcePointFeatures,
    sourceLineFeatures,
    sourcePolygonFeatures,
    renderedPointFeatures: sampledPoints.items.length,
    renderedLineFeatures: sampledLines.items.length,
    sampledPoints: sampledPoints.sampled,
    sampledLines: sampledLines.sampled,
    simplifiedGeometries,
  };
}
