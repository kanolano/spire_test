import "./styles/app.css";

import { boot } from "./actions";
import { mountArtDefs } from "./art/defs";
import { artSheetRequested, renderArtSheet } from "./art/sheet";
import { reducedMotion } from "./director";
import { wireAudioUnlock } from "./audio";
import { wireDrag } from "./drag";
import { wireInput } from "./input";
import { mountParticles } from "./particles";
import { render } from "./render";
import { onRender } from "./store";
import { wireTooltips } from "./ui/tooltip";

document.body.classList.toggle("no-motion", reducedMotion());

// The art contact sheet is a development view, not part of the game.
if (artSheetRequested()) {
  renderArtSheet();
} else {
  mountArtDefs();
  onRender(render);
  wireTooltips();
  wireInput();
  wireDrag();
  wireAudioUnlock();
  mountParticles();
  void boot();
}
