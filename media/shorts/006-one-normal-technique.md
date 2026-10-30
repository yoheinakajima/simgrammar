# Short 6. The one AI technique that's normal

Vertical, about 55 seconds, about 100 words of narration. One finding, from technique maturity (chapter 7, episode 6). Any scratch voice is synthetic and disclosed on screen; the release uses the host's voice. Footage: Microsoft Flight Simulator (2020), and a short credited clip from the Project Genie announcement (`media/rights.yaml`).

## 0:00 to 0:05. The finding

**Picture.** Microsoft Flight Simulator, a low pass over a city at dusk. A graphic frame counter, added in the edit, doubles.

**Frame.** count kind=tally of=technique field=maturity current=maturity-shipped-mainstream

**On screen.** {{stat:n_technique_shipped_mainstream}} of {{count:technique}} AI techniques has become normal in games.

**Voice.** Of the AI techniques in our dataset, exactly one has become normal in games, and it never touches the simulation.{{assert:n_technique_shipped_mainstream == 1}}

## 0:05 to 0:22. What it is

**Picture.** Split screen: frames the game drew on the left, generated frames slotted between them on the right.

**Frame.** chain nodes="rendered-frame:A frame the game drew,neural-rendering-shaders:A generated frame,rendered-frame:The next frame it drew"

**Voice.** It's neural rendering: upscaling, and frames predicted between the ones the game drew. More than 250 titles support multi-frame generation, and Flight Simulator has frame generation too [@src-nvidia-2026-dlss-4-5; @src-pcgamingwiki-2026-msfs-2020].{{assert:field.neural-rendering-shaders.maturity == shipped-mainstream}}

## 0:22 to 0:38. Why it spread

**Picture.** The game's save file, replay timeline, and network code as three boxes; the generated frames pass beside them without connecting.

**Frame.** compare a="The simulation" a_items="save-file:Saves,replay:Replays,monitor:Multiplayer" b="Generated frames" b_items="neural-rendering-shaders:Between two real ones"

**Voice.** A generated frame sits between two real ones, and the simulation never knows. Saves, replays, and multiplayer stay exactly as they were.{{assert:field.neural-rendering-shaders.determinism_impact == preserves}}

## 0:38 to 0:52. The other end

**Picture.** A Project Genie world, with a graphic timer counting down from sixty seconds.

**Frame.** mockup kind=standin from=genie-world-models title="A generated world" subject="A world model's playable scene" chart=timer lines="60|Each world is capped at 60 seconds of play"

**Voice.** The models that would replace the game world itself are still prototypes. Google's Project Genie, built on Genie 3, caps each world at sixty seconds to save compute [@src-techcrunch-2026-project-genie].{{assert:field.genie-world-models.maturity == prototype}}

## 0:52 to 0:57. End card

**On screen.** Episode 6: What AI shipped. simgrammar.com
