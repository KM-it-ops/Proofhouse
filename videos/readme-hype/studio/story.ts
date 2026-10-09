import type { Data } from "./timeline.ts";

// Authored for this video. An illustration of the flow, not a recorded run.
export const story: Data = {
  objective: "Turn my meeting notes into a Friday update.",
  qa: [
    { q: "What should this prompt produce?", a: "A Friday update of under 200 words, built from my raw notes from the week's meetings." },
    { q: "Who reads it?", a: "My director, on her phone." },
    { q: "What tone?", a: "Plain and calm. No hype." },
    { q: "What must it include?", a: "Wins, blockers, and what I need from her." },
    { q: "What must it avoid?", a: "Names of people outside my team." },
    { q: "What if the notes are unclear?", a: "Ask me. Never guess a number." },
    { q: "How should it end?", a: "One line saying what happens next." },
  ],
  sections: [
    {
      title: "Task",
      paras: [
        "Turn the raw meeting notes below into a Friday update of under 200 words for a director who reads on her phone. Write in plain, calm language with no hype. Include wins, blockers, and what the writer needs from her. End with one line saying what happens next.",
      ],
    },
    {
      title: "Weekly loop",
      paras: [
        "Trigger: every Friday at 3:00 PM, once the week's notes are saved.",
        "Verify: the update is under 200 words and has wins, blockers, and the ask.",
        "Exit: stop when the writer approves the draft. Ask before sending anything.",
      ],
    },
    {
      title: "Rules",
      paras: [
        "Leave out the names of people outside the writer's team.",
        "Never guess a number. Use the writer's figures exactly as written.",
      ],
    },
  ],
};

export const MODEL_HEAD = "OPTIMIZED PROMPT · GEMINI 3.8 FLASH";
