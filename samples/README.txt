SAMPLE CURVES
=============

Ready-made curves to try AutoEQ Studio with. A fresh copy of the app starts with one of them already chosen
(Truthear GATe to the 5128 diffuse-field target), so you can press Run straight away.

To use another one: Add… next to Measurement (or Target) and pick the files here (a device's L and R files
together), or find them with Find… (This PC).

targets\
  Diffuse field 5128 -1dB per octave     for measurements made on a B&K 5128 (the GATe, EarPods and Astro here)
  HMS II.3 AutoEq in-ear                 for measurements made on a Head Acoustics HMS

measurements\
  Truthear GATe - B&K 5128, 10 seatings  an IEM measured 10 times (5 per ear); the app averages them
  Apple EarPods - B&K 5128               earbuds, left and right
  Truthear Gate - 711 coupler            the same IEM as above on another kind of rig: its curve differs,
                                         mostly in the treble (the app marks rigs that don't match the target)
  Astro A20X headset - Gadgetry          a gaming headset, left and right

format tests\
  Files written the way other PCs and programs write them. Each should be added without problems and look
  like the EarPods curve, except the last one, which should be refused with a clear message:
    decimal commas and semicolons  (as saved on a PC set to a European language, e.g. by Excel)
    saved as Unicode (UTF-16)      (as Notepad's "Unicode" option or PowerShell saves text)
    Not a frequency response       (a text file that isn't a curve)

Sources: the AutoEq project (github.com/jaakkopasanen/AutoEq), listener800's 5128 database, Earphones Archive
and Gadgetry Tech on squig.link. They're shared here only so the app can be tried out.
