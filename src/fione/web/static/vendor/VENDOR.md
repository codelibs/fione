# Vendored front-end libraries

Served from `/static/vendor/` so the UI works offline (no CDN). Files are copied unmodified
from the npm tarballs below; each tarball was checked against the registry's `dist.integrity`
(sha512) before copying. Update by replacing the files and every line of this table.

| Library | Version | Licence | Source |
|---|---|---|---|
| htmx | 2.0.11 | 0BSD | https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.11.tgz (`dist/htmx.min.js`, `LICENSE`) |
| Apache ECharts | 6.1.0 | Apache-2.0 | https://registry.npmjs.org/echarts/-/echarts-6.1.0.tgz (`dist/echarts.min.js`, `LICENSE`, `NOTICE`, `licenses/LICENSE-d3`) |
| ZRender (bundled in `echarts.min.js`) | 6.1.0 | BSD-3-Clause | https://registry.npmjs.org/zrender/-/zrender-6.1.0.tgz (`LICENSE`, saved as `echarts/LICENSE-zrender`) |

`echarts.min.js` also embeds parts of d3.js (BSD-3-Clause, `echarts/LICENSE-d3`) and tslib
helpers (0BSD). All of these are allowed by the licence policy (see the README).

## sha256

```
d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717  htmx/htmx.min.js
d3d2456f76414f2456104660ebd65aff1c04cd7966b942bdabd63f3cdb316a38  htmx/LICENSE
b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0  echarts/echarts.min.js
634293835b43a6dd2094fa39182a3d9a6b9ca43b7fdb9ac354e8037af2a3093a  echarts/LICENSE
d491d358344f842685c1b1585970999db65fe30ecf7ef3867af8814f4016c016  echarts/NOTICE
e1211892da0b0e0585b7aebe8f98c1274fba15bafe47fa1f4ee8a7a502c06304  echarts/LICENSE-d3
a681e9d183c72b4af4856935893805eb48c08f0f5a3f260203db7444c20fb98a  echarts/LICENSE-zrender
```

Check with `shasum -a 256 -c` from this directory (paste the block above into a file).

## Notes

- htmx runs with `allowEval: false`, `includeIndicatorStyles: false` and
  `attributesToSettle: ["class"]` (set in `templates/base.html`), so it works under the UI's
  `script-src 'self'; style-src 'self'` Content-Security-Policy (no inline styles, no
  `style` attributes copied while settling); the indicator styles live in `css/app.css`.
- ECharts is loaded only by pages that draw charts.
