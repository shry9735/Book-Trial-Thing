# Meet the Breadboard

A breadboard is a plastic rectangle full of little holes. It looks like nothing. It is actually the single most useful object on your workbench, and here is why: it lets you build a circuit without soldering anything, and it lets you take that circuit apart thirty seconds later when you realize you did it wrong.

You will do it wrong. Everyone does it wrong. That is the whole point of a breadboard.

## The holes are already connected

This is the part that trips people up. The holes are not independent. Underneath the plastic, metal strips connect them in groups, and if you don't know which groups, your circuit will do something baffling.

There are two patterns:

**The power rails** run along the long edges, usually marked with a red line and a blue line. Every hole in a red rail is connected to every other hole in that red rail, all the way down. Same for blue. These are for power and ground — the two connections almost everything needs.

**The terminal strips** fill the middle. These run *across* the board in rows of five, and there's a channel down the center that splits each row in half. So holes 1–5 of a row are connected to each other, holes 6–10 are connected to each other, and the two halves are **not** connected.

> **ENGINEERING NOTE — Why the center channel exists**
> That gap isn't decoration. Chips with legs on both sides — like an Arduino's brain chip — straddle the channel so each leg lands in its own isolated row. Without the gap, every leg on the left would short to the leg opposite it, and the chip would do nothing but get hot. The channel is what makes chips usable at all.

## Reading a breadboard like a map

When you look at a breadboard, don't see holes. See *groups of holes that are already wired together*. Once you see it that way, building a circuit becomes a much simpler question: which group does this leg need to be in?

A component leg plugged into row 12-left is electrically the same as a wire plugged into row 12-left. They're touching, as far as electricity is concerned. That's how you connect two things: put them in the same group.

And that's how you *accidentally* connect two things, too. If you meant to put an LED leg in row 12 and it slipped into row 11, nothing will tell you. No spark, no error message. The circuit just won't work, and you'll spend ten minutes checking your code when the problem is a leg one row off.

## Before you build anything

Get in the habit of these three:

1. **Power rails first.** Run your red and blue jumpers from the power source to the rails before you place a single component. Then everything you add has power available right next to it.
2. **Push all the way down.** A leg that's only half-seated makes contact *sometimes*. Intermittent connections are the hardest bug to find, because the circuit works right up until you touch it.
3. **Tug test.** When you think you're done, gently pull each wire. Anything that comes out was never really in.

That last one takes fifteen seconds and will save you an hour.
