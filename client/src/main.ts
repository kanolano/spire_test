import "./styles/app.css";

import { boot } from "./actions";
import { wireInput } from "./input";
import { render } from "./render";
import { onRender } from "./store";
import { wireTooltips } from "./ui/tooltip";

onRender(render);
wireTooltips();
wireInput();
void boot();
