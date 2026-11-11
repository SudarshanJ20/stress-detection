# Still assets, instrument and design references

## Bundled assets

- `public/images/forest.webp`: **Jonas Tebbe**, “Pathway along forest during foggy day,” [original Unsplash photograph](https://unsplash.com/photos/pathway-along-forest-during-foggy-day-oFxxpPKwd84). Original image endpoint: `images.unsplash.com/photo-1502143655672-dbd02dd6abb6`. Downloaded 2026-11-12; resized to a maximum of 1400 × 1700 and encoded as WebP. This is a free photograph under the [Unsplash License](https://unsplash.com/license), not an Unsplash+ asset. The license permits downloading, modifying and using this image, including local bundling; attribution is appreciated and provided here. No identifiable person is depicted. No design-reference imagery is bundled.
- `public/fonts/editorial-latin.ttf`: **Cormorant Garamond**, copyright 2015 the Cormorant Project Authors. [Upstream Google Fonts files](https://github.com/google/fonts/tree/main/ofl/cormorantgaramond). Latin/punctuation subset made with fontTools; variable weight retained. SIL Open Font License 1.1 is reproduced in `public/fonts/OFL.txt`. The interface sans-serif uses system fonts, with no external font request.
- Icons: `lucide-react` 0.577.0, ISC license. [Lucide licensing](https://lucide.dev/license). Original Still layout and logo composition; no implied certification or medical endorsement.
- Motion for React 14.12.0 (MIT), GSAP 3.15.1 ([standard no-charge license](https://gsap.com/standard-license/)). GSAP is lazy-loaded only for the landing three-step narrative and cleaned up on navigation. Native scrolling is retained. Lenis and shadcn/ui are not needed: native controls/dialogs meet the current flows with fewer dependencies.

## GAD-7: wording, scoring and permission

- [University of Washington National HIV Curriculum published form](https://www.hiv.uw.edu/page/mental-health-screening/gad-7): seven English items, response choices, two-week timeframe and the explicit statement that no permission is required to reproduce, translate, display or distribute. Its developer attribution is retained in the UI and reports.
- [Published GAD-7 form and scoring guide hosted by The REACH Institute](https://thereachinstitute.org/wp-content/uploads/2022/09/GAD-7_Anxiety-updated_2022.pdf): sum 0–21, bands 0–4 minimal, 5–9 mild, 10–14 moderate, **15–21 severe**. This guide resolves an imprecise “greater than 15” wording on the UW interactive page; 15 is included in severe. No cutoff or category was chosen from our data.
- Developers: Robert L. Spitzer, Janet B.W. Williams, Kurt Kroenke and colleagues, with an educational grant from Pfizer Inc. The instrument is not presented as our invention. Permission to reproduce is not a claim that Still has clinical endorsement.
- `lib/gad7.json` is the shared frontend/backend form contract. Every response must be an integer 0–3; all seven are required. The supplementary difficulty response is optional and unscored. GAD-7 categories are not UBFC CSAI scores and are not merged with camera signals.

## References inspected before implementation

- [SMPLY Studio: Yoga & Wellness Studio](https://dribbble.com/shots/27025711-Yoga-Wellness-Studio-Website-Design-Calm-Minimal-Design): earthy palette, readable hierarchy and spacious primary actions.
- [Abu Hossain: Smart Wellness Website](https://dribbble.com/shots/26992648-Smart-Wellness-Website-Design): restrained warm color and a clear hero-to-action hierarchy.
- [Kinfolk](https://www.kinfolk.com/): editorial serif typography, quiet image placement and generous negative space.
- [SOLI Wellness Studio concept](https://www.behance.net/gallery/243458745/SOLI-Wellness-Studio-Website-Concept): search description inspected, but the full Behance page returned 403. It was not used as an accessible visual reference.

These are inspiration links, not asset sources. Still uses its own composition, copy, controls and data flows. No proprietary layout, testimonials, credentials, ratings or usage figures were copied.
