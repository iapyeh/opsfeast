import test from "node:test";
import assert from "node:assert/strict";
import {siteAssetUrl} from "../web/assets/site-assets.mjs";

test("unset images use the bundled product mark without changing saved data", () => {
  const site = {logo:null,avatar:null};
  assert.equal(siteAssetUrl(site,"logo"),"/assets/mark.svg");
  assert.equal(siteAssetUrl(site,"avatar"),"/assets/mark.svg");
  assert.deepEqual(site,{logo:null,avatar:null});
});
test("custom assets keep their persistent references and invalid references fail", () => {
  const id="a".repeat(64)+".png";
  assert.equal(siteAssetUrl({avatar:id},"avatar"),`/site-assets/${id}`);
  assert.throws(() => siteAssetUrl({avatar:"../private"},"avatar"));
  assert.throws(() => siteAssetUrl({},"unknown"));
});
