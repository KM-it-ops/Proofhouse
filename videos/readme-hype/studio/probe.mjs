import { makeTimeline } from "./timeline.ts";
import { story } from "./story.ts";
const t = makeTimeline(story);
console.log("clarifyEnd", t.clarifyEnd, "rows", t.rows.map((r) => [r.clickAt, r.endAt].join("/")).join(" "));
console.log("lines", t.prompt.lines.length, "height", Math.round(t.prompt.height), "(viewport 628)");
t.traces.forEach((x) => console.log(x.q, x.phrase.slice(0, 24), x.rects.length, "rects @", x.at, x.end.map(Math.round)));
console.log("stops sorted", t.stops.every((s, i) => i === 0 || s.f > t.stops[i - 1].f));
