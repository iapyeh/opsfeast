// Prototype-private localization interface, not yet a public presentation SDK.
import zhTW from "./locales/zh-TW.mjs";

export const defaultLocale = "zh-TW";
export const supportedLocales = Object.freeze(["zh-TW"]);
const catalogs = {"zh-TW": zhTW};

export function resolveLocale(preferences = []) {
  for (const preference of preferences) {
    if (typeof preference !== "string") continue;
    const match = supportedLocales.find(locale => locale.toLowerCase() === preference.toLowerCase());
    if (match) return match;
  }
  return defaultLocale;
}

export function getMessages(locale) {
  return catalogs[resolveLocale([locale])];
}

export function translate(locale, key, parameters = {}) {
  const message = key.split(".").reduce((value, part) => value?.[part], getMessages(locale));
  if (typeof message !== "string") throw new Error(`Missing message: ${key}`);
  return message.replace(/\{(\w+)\}/g, (_, name) => {
    if (!Object.hasOwn(parameters, name)) throw new Error(`Missing parameter: ${name}`);
    return String(parameters[name]);
  });
}

export function formatNumber(value, locale = defaultLocale, options = {}) {
  return new Intl.NumberFormat(resolveLocale([locale]), options).format(value);
}

export function formatDateTime(value, locale = defaultLocale, timeZone = "Asia/Taipei") {
  return new Intl.DateTimeFormat(resolveLocale([locale]), {
    dateStyle: "medium", timeStyle: "medium", timeZone
  }).format(new Date(value));
}

export function readLocale(storage, browserLanguages = []) {
  let saved;
  try { saved = storage?.getItem("opsfeast.ui.locale"); } catch { /* Storage may be unavailable. */ }
  return resolveLocale([saved, ...browserLanguages]);
}

export function saveLocale(storage, locale) {
  if (!supportedLocales.includes(locale)) throw new Error(`Unsupported locale: ${locale}`);
  try { storage?.setItem("opsfeast.ui.locale", locale); } catch { /* Rendering still works. */ }
}
