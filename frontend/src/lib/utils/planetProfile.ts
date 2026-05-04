/** Planet bodies supported for basemap selection. */
export type PlanetBody = "earth" | "mars" | "moon";

/** Leaflet basemap profile used for a detected planetary body. */
export type PlanetProfile = {
  body: PlanetBody;
  label: string;
  tileUrl: string;
  attribution: string;
  maxZoom: number;
};

/** Basemap configuration keyed by supported planetary body. */
export const PLANET_PROFILES: Record<PlanetBody, PlanetProfile> = {
  earth: {
    body: "earth",
    label: "Earth",
    tileUrl: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  },
  mars: {
    body: "mars",
    label: "Mars",
    tileUrl:
      "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://openplanetarymap.org/">OpenPlanetaryMap</a>',
    maxZoom: 9,
  },
  moon: {
    body: "moon",
    label: "Moon",
    tileUrl:
      "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://openplanetarymap.org/">OpenPlanetaryMap</a>',
    maxZoom: 9,
  },
};

const MARS_HINTS = /(mars|martian|mola|jezero|olympus|valles)/i;
const MOON_HINTS = /(moon|lunar|selene|apollo|chang[\'\- ]?e|artemis)/i;
const OTHER_PLANETARY_HINTS = /(mercury|venus|jupiter|saturn|uranus|neptune|pluto|ceres|vesta)/i;

/** Guesses body from S3 key naming hints and defaults to Earth. */
export function detectPlanetBodyFromKey(key: string): PlanetBody {
  if (MARS_HINTS.test(key)) return "mars";
  if (MOON_HINTS.test(key)) return "moon";
  return "earth";
}

/** Flags likely planetary data that does not currently have a dedicated basemap. */
export function isLikelyPlanetaryButUnsupported(key: string): boolean {
  return OTHER_PLANETARY_HINTS.test(key);
}

/** Resolves a full basemap profile for a given object key. */
export function getPlanetProfileForKey(key: string): PlanetProfile {
  return PLANET_PROFILES[detectPlanetBodyFromKey(key)];
}
