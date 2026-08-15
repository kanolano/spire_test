import "./styles/app.css";

import { boot } from "./actions";
import { reducedMotion } from "./director";
import { wireInput } from "./input";
import { render } from "./render";
import { onRender } from "./store";
import { wireTooltips } from "./ui/tooltip";

document.body.classList.toggle("no-motion", reducedMotion());

onRender(render);
wireTooltips();
wireInput();
void boot();
