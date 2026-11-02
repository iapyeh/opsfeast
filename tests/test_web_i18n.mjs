import test from "node:test";
import assert from "node:assert/strict";
import {defaultLocale, supportedLocales, resolveLocale, getMessages, translate, readLocale,
  saveLocale, formatNumber, formatDateTime} from "../web/assets/i18n.mjs";

test("only approved authoring locale is available; unsupported browser languages fall back", () => {
  assert.deepEqual(supportedLocales, ["zh-TW"]);
  assert.equal(defaultLocale, "zh-TW");
  assert.equal(resolveLocale(["en-US", "de"]), "zh-TW");
  assert.equal(resolveLocale([null, "zh-tw"]), "zh-TW");
  assert.equal(getMessages("en").shell.guest, "尚未登入");
});
test("messages interpolate whole sentences and expose missing keys/parameters", () => {
  assert.equal(translate("zh-TW", "demo.state", {state:"收尾中"}), "操作狀態：收尾中");
  assert.throws(() => translate("zh-TW", "missing.key"), /Missing message/);
  assert.throws(() => translate("zh-TW", "demo.state"), /Missing parameter/);
});
test("browser preference storage is optional and unsupported languages cannot be saved", () => {
  const unavailable = {getItem() {throw Error();}, setItem() {throw Error();}};
  assert.equal(readLocale(unavailable, ["en"]), "zh-TW");
  assert.doesNotThrow(() => saveLocale(unavailable, "zh-TW"));
  assert.throws(() => saveLocale(unavailable, "en"), /Unsupported locale/);
  let saved;
  const storage = {setItem(key, value) {saved = [key, value];}, getItem() {return saved?.[1];}};
  saveLocale(storage, "zh-TW");
  assert.deepEqual(saved, ["opsfeast.ui.locale", "zh-TW"]);
  assert.equal(readLocale(storage, ["en"]), "zh-TW");
});
test("formatting keeps timezone separate from locale", () => {
  assert.equal(formatNumber(12345), "12,345");
  const instant = "2026-11-01T00:00:00Z";
  assert.notEqual(formatDateTime(instant, "zh-TW", "Asia/Taipei"), formatDateTime(instant, "zh-TW", "UTC"));
});

test('every settings card has its own readable title and description',()=>{
  for(const category of Object.values(getMessages('zh-TW').settings.categories)){
    assert.equal(typeof category.title,'string');
    assert.equal(typeof category.text,'string');
    assert.ok(category.text.length>0);
  }
});
