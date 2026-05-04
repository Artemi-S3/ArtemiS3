<script lang="ts">
  /** Geospatial map preview renderer using Leaflet plus optional worker prep. */
  import L from "leaflet";
  import { onDestroy, tick } from "svelte";
  import type { GeospatialPreviewResult } from "../schemas/geospatial";
  import { loadGeospatialPreviewFromUrl } from "../utils/geospatialPreview";
  import {
    getPlanetProfileForKey,
    isLikelyPlanetaryButUnsupported,
    type PlanetProfile,
  } from "../utils/planetProfile";
  import {
    prepareFeatureCollectionForRendering,
    type GeospatialRenderPrepMessage,
    type GeospatialRenderPreparation,
  } from "../utils/geospatialRenderPrep";

  export let fileKey = "";
  export let fileSize = 0;
  export let previewUrl = "";

  let mapContainer: HTMLDivElement;
  let map: L.Map | null = null;
  let pointLayer: L.GeoJSON | null = null;
  let lineLayer: L.GeoJSON | null = null;
  let loading = false;
  let errorMessage: string | null = null;
  let metadata: GeospatialPreviewResult | null = null;
  let renderPrep: GeospatialRenderPreparation | null = null;
  let requestId = 0;
  let activePlanetProfile: PlanetProfile = getPlanetProfileForKey(fileKey);
  let showPoints = true;
  let showLines = true;

  $: if (fileKey && previewUrl) {
    void renderMapPreview(fileKey, fileSize, previewUrl);
  }

  $: {
    // Explicitly reference toggles so Svelte re-runs this block when they change.
    showPoints;
    showLines;
    if (!loading && map && (pointLayer || lineLayer)) {
      syncVisibleLayers();
      fitToVisibleLayers();
    }
  }

  /** Returns filename-like display text from an object key. */
  function displayName(key: string): string {
    const segments = key.split("/").filter(Boolean);
    return segments[segments.length - 1] || key;
  }

  /** Indicates whether coordinate normalization warning should be shown. */
  function showNormalizationNotice(result: GeospatialPreviewResult | null): boolean {
    if (!result) return false;
    return (
      result.normalization.swappedCoordinateOrder ||
      result.normalization.wrappedLongitudes
    );
  }

  /** Flags likely planetary datasets without dedicated basemap support. */
  function shouldShowUnsupportedPlanetaryNotice(key: string): boolean {
    return activePlanetProfile.body === "earth" && isLikelyPlanetaryButUnsupported(key);
  }

  /** Indicates whether sampling/simplification notice should be displayed. */
  function shouldShowPerformanceNotice(prep: GeospatialRenderPreparation | null): boolean {
    if (!prep) return false;
    return prep.sampledLines || prep.sampledPoints || prep.simplifiedGeometries > 0;
  }

  /** Initializes Leaflet map and base tiles for the selected planet profile. */
  function ensureMap(profile: PlanetProfile) {
    if (!mapContainer || map) return;

    const nextMap = L.map(mapContainer, {
      preferCanvas: true,
      zoomControl: true,
      worldCopyJump: false,
    });
    if (!nextMap) return;

    map = nextMap;

    L.tileLayer(profile.tileUrl, {
      maxZoom: profile.maxZoom,
      attribution: profile.attribution,
    }).addTo(map);

    map.setView([20, 0], 2);
  }

  /** Removes rendered point/line layers from the map and clears references. */
  function clearLayers() {
    if (map && pointLayer) {
      map.removeLayer(pointLayer);
    }
    if (map && lineLayer) {
      map.removeLayer(lineLayer);
    }
    pointLayer = null;
    lineLayer = null;
  }

  /** Builds point feature layer styling for map display. */
  function buildPointLayer(prep: GeospatialRenderPreparation): L.GeoJSON {
    return L.geoJSON(prep.pointCollection as any, {
      pointToLayer: (_feature, latLng) =>
        L.circleMarker(latLng, {
          radius: 2,
          color: "#f59e0b",
          weight: 1,
          fillColor: "#fbbf24",
          fillOpacity: 0.55,
        }),
    });
  }

  /** Builds line and polygon layer styling for map display. */
  function buildLineLayer(prep: GeospatialRenderPreparation): L.GeoJSON {
    return L.geoJSON(prep.lineCollection as any, {
      style: (feature) => {
        const geometryType = feature?.geometry?.type ?? "";
        if (geometryType === "Polygon" || geometryType === "MultiPolygon") {
          return {
            color: "#f59e0b",
            weight: 1.2,
            opacity: 0.7,
            fillOpacity: 0.08,
          };
        }
        return {
          color: "#f59e0b",
          weight: 1,
          opacity: 0.6,
          fillOpacity: 0,
        };
      },
      pointToLayer: (_feature, latLng) =>
        L.circleMarker(latLng, {
          radius: 2,
          color: "#f59e0b",
          weight: 1,
          fillColor: "#fbbf24",
          fillOpacity: 0.45,
        }),
    });
  }

  /** Reattaches active layers according to current visibility toggles. */
  function syncVisibleLayers() {
    if (!map) return;

    if (pointLayer) {
      map.removeLayer(pointLayer);
    }
    if (lineLayer) {
      map.removeLayer(lineLayer);
    }

    if (showPoints && pointLayer) {
      pointLayer.addTo(map);
    }
    if (showLines && lineLayer) {
      lineLayer.addTo(map);
    }

    requestAnimationFrame(() => {
      map?.invalidateSize();
    });
  }

  /** Fits the map viewport to visible layer bounds or resets to default view. */
  function fitToVisibleLayers() {
    if (!map) return;

    const candidates: L.GeoJSON[] = [];
    if (showPoints && pointLayer) candidates.push(pointLayer);
    if (showLines && lineLayer) candidates.push(lineLayer);
    if (candidates.length === 0) return;

    for (const layer of candidates) {
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds.pad(0.12));
        return;
      }
    }

    map.setView([20, 0], 2);
  }

  /** Prepares feature data for rendering, preferring worker execution when available. */
  async function prepareRenderData(
    featureCollection: GeospatialPreviewResult["featureCollection"],
  ): Promise<GeospatialRenderPreparation> {
    const canUseWorker =
      typeof window !== "undefined" && typeof Worker !== "undefined";

    if (!canUseWorker) {
      return prepareFeatureCollectionForRendering(featureCollection);
    }

    try {
      return await new Promise<GeospatialRenderPreparation>((resolve, reject) => {
        const worker = new Worker(
          new URL("../workers/geospatialRenderPrep.worker.ts", import.meta.url),
          { type: "module" },
        );

        const cleanup = () => {
          worker.onmessage = null;
          worker.onerror = null;
          worker.terminate();
        };

        worker.onmessage = (event: MessageEvent<GeospatialRenderPrepMessage>) => {
          cleanup();
          if (event.data.ok) {
            resolve(event.data.data);
            return;
          }
          reject(new Error(event.data.error));
        };

        worker.onerror = () => {
          cleanup();
          reject(new Error("Worker failed while preparing map render data."));
        };

        worker.postMessage({ featureCollection });
      });
    } catch {
      return prepareFeatureCollectionForRendering(featureCollection);
    }
  }

  /** Loads, prepares, and renders the next geospatial preview payload. */
  async function renderMapPreview(nextKey: string, nextSize: number, nextUrl: string) {
    const token = ++requestId;
    const nextPlanetProfile = getPlanetProfileForKey(nextKey);

    if (map && activePlanetProfile.body !== nextPlanetProfile.body) {
      map.remove();
      map = null;
      pointLayer = null;
      lineLayer = null;
    }

    activePlanetProfile = nextPlanetProfile;
    loading = true;
    errorMessage = null;
    metadata = null;
    renderPrep = null;
    clearLayers();

    await tick();
    ensureMap(activePlanetProfile);

    if (!map) {
      loading = false;
      errorMessage = "Map container failed to initialize.";
      return;
    }

    try {
      const result = await loadGeospatialPreviewFromUrl({
        key: nextKey,
        size: nextSize,
        previewUrl: nextUrl,
      });
      if (token !== requestId) return;

      const prepared = await prepareRenderData(result.featureCollection);
      if (token !== requestId) return;

      metadata = result;
      renderPrep = prepared;

      showPoints = true;
      showLines = !(
        prepared.renderedLineFeatures > 1500 ||
        prepared.sourceLineFeatures + prepared.sourcePolygonFeatures > 3000
      );

      pointLayer = buildPointLayer(prepared);
      lineLayer = buildLineLayer(prepared);

      syncVisibleLayers();
      fitToVisibleLayers();
    } catch (error) {
      if (token !== requestId) return;
      errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to render geospatial preview. Download this file instead.";
    } finally {
      if (token === requestId) {
        loading = false;
      }
    }
  }

  /** Cleans up pending work and Leaflet resources when component unmounts. */
  onDestroy(() => {
    requestId += 1;
    clearLayers();
    if (map) {
      map.remove();
      map = null;
    }
  });
</script>

<div class="space-y-2">
  <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300">
    <span class="truncate font-semibold">Map preview: {displayName(fileKey)}</span>
    <span class="rounded border border-slate-500/60 bg-slate-900/70 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-100">
      Body: {activePlanetProfile.label}
    </span>
    {#if metadata}
      <span>
        {metadata.featureCount} feature{metadata.featureCount === 1 ? "" : "s"} |
        {metadata.geometryTypes.join(", ") || "Unknown geometry"}
      </span>
    {/if}
  </div>

  {#if renderPrep}
    <div class="flex flex-wrap items-center justify-between gap-3 text-xs">
      <div class="flex items-center gap-3 text-slate-200">
        <label class="inline-flex items-center gap-1">
          <input type="checkbox" bind:checked={showPoints} class="h-3.5 w-3.5 accent-amber-400" />
          <span>Points ({renderPrep.renderedPointFeatures}/{renderPrep.sourcePointFeatures})</span>
        </label>
        <label class="inline-flex items-center gap-1">
          <input type="checkbox" bind:checked={showLines} class="h-3.5 w-3.5 accent-amber-400" />
          <span>Lines/Polygons ({renderPrep.renderedLineFeatures}/{renderPrep.sourceLineFeatures + renderPrep.sourcePolygonFeatures})</span>
        </label>
      </div>
    </div>
  {/if}

  {#if showNormalizationNotice(metadata)}
    <p class="text-xs text-amber-200/90">
      Coordinates were normalized for display ({metadata?.normalization.swappedCoordinateOrder
        ? "lat/lon order corrected"
        : "lon wrapped to -180..180"}
      ).
    </p>
  {/if}

  {#if shouldShowPerformanceNotice(renderPrep)}
    <p class="text-xs text-amber-200/90">
      Large dataset optimization applied (sampling/simplification) for faster preview.
    </p>
  {/if}

  {#if shouldShowUnsupportedPlanetaryNotice(fileKey)}
    <p class="text-xs text-slate-300/90">
      This looks like unsupported planetary data. Earth basemap is being used as fallback.
    </p>
  {/if}

  <div class="relative h-[560px] w-full overflow-hidden rounded border border-slate-600/55 bg-slate-950/75">
    <div bind:this={mapContainer} class="h-full w-full"></div>

    {#if loading}
      <div
        class="absolute inset-0 z-[500] flex items-center justify-center bg-slate-950/55 p-4 text-sm text-slate-100"
      >
        Loading geospatial preview...
      </div>
    {/if}

    {#if errorMessage}
      <div
        class="absolute inset-0 z-[600] flex items-center justify-center bg-slate-950/75 p-5 text-center text-sm text-amber-100"
      >
        {errorMessage}
      </div>
    {/if}
  </div>
</div>
