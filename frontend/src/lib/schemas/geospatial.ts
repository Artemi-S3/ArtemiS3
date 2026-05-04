/** Supported file extensions for map preview parsing. */
export const SUPPORTED_GEOSPATIAL_EXTENSIONS = [
  ".geojson",
  ".kml",
  ".kmz",
] as const;

/** Maximum input size allowed for browser-side geospatial preview parsing. */
export const GEOSPATIAL_SIZE_CAP_BYTES = 15 * 1024 * 1024;

/** Normalized geospatial source format supported by preview parser. */
export type GeospatialFormat = "geojson" | "kml" | "kmz";

/** GeoJSON geometry types accepted by the preview pipeline. */
export type GeoJsonGeometryType =
  | "Point"
  | "MultiPoint"
  | "LineString"
  | "MultiLineString"
  | "Polygon"
  | "MultiPolygon"
  | "GeometryCollection";

/** Simplified geometry shape used by parser/render helpers. */
export type GeoJsonGeometry = {
  type: GeoJsonGeometryType;
  coordinates?: unknown;
  geometries?: GeoJsonGeometry[];
};

/** Simplified GeoJSON feature shape used by parser/render helpers. */
export type GeoJsonFeature = {
  type: "Feature";
  geometry: GeoJsonGeometry | null;
  properties: Record<string, unknown> | null;
  id?: string | number;
};

/** Normalized feature collection generated from preview inputs. */
export type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

/** Parsed geospatial preview payload and metadata for display. */
export type GeospatialPreviewResult = {
  format: GeospatialFormat;
  featureCollection: GeoJsonFeatureCollection;
  featureCount: number;
  geometryTypes: GeoJsonGeometryType[];
  normalization: {
    swappedCoordinateOrder: boolean;
    wrappedLongitudes: boolean;
    coordinatePairs: number;
    validCoordinateRatio: number;
  };
};
