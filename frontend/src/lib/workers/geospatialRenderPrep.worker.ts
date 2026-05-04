/// <reference lib="webworker" />

/** Web Worker entrypoint for geospatial render preparation. */
import {
  prepareFeatureCollectionForRendering,
  type GeospatialRenderPrepMessage,
} from "../utils/geospatialRenderPrep";
import type { GeoJsonFeatureCollection } from "../schemas/geospatial";

type WorkerRequest = {
  featureCollection: GeoJsonFeatureCollection;
};

/** Handles render-preparation requests and posts success/error responses. */
self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  try {
    const prepared = prepareFeatureCollectionForRendering(
      event.data.featureCollection,
    );
    const response: GeospatialRenderPrepMessage = {
      ok: true,
      data: prepared,
    };
    self.postMessage(response);
  } catch (error) {
    const response: GeospatialRenderPrepMessage = {
      ok: false,
      error: error instanceof Error ? error.message : "Render preparation failed.",
    };
    self.postMessage(response);
  }
};

export {};
