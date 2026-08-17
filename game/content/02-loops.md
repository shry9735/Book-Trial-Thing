# Your First Loop

Say you want your robot to blink an LED five times. You could write the blink instructions five times in a row. It would work. It would also be six lines of nearly identical code, and when you decide you want six blinks instead, you have to go back and add another copy — carefully, without typos.

A loop is how you say "do this again" without writing it again.

## The shape of a loop

Every loop needs three things, and if you can name all three, you can write any loop:

- **Where to start.** A counter set to some beginning value.
- **When to stop.** A condition checked before each pass.
- **How to move.** Something that changes the counter, so you eventually *reach* the stopping point.

In Arduino code, all three go on one line:

```cpp
for (int i = 0; i < 5; i++) {
  digitalWrite(LED_PIN, HIGH);
  delay(200);
  digitalWrite(LED_PIN, LOW);
  delay(200);
}
```

Read it out loud as a sentence: *start `i` at zero; keep going while `i` is less than five; add one to `i` each time around.* The instructions between the braces run once per pass. Five passes, five blinks.

## The counter starts at zero

This surprises everyone at first. `i` starts at 0, not 1, and the loop stops when `i` reaches 5 — which means the values it actually takes are 0, 1, 2, 3, 4. That's five numbers. Count them.

Programmers count from zero almost everywhere, and once you're used to it, `i < 5` reading as "five times" becomes automatic.

> **ENGINEERING NOTE — Off-by-one errors**
> The most common loop bug in the world is running one time too many or one time too few. It has a name — the *off-by-one error* — because it happens so often it needed one. The usual culprit is `<=` where you meant `<`. If your loop does six blinks when you asked for five, check that comparison first. You will be right most of the time.

## When you don't know how many times

Sometimes you don't want a fixed count. You want to keep going until something happens — until a button is pressed, until the sensor reads under 10 cm, until the battery dies.

That's a `while` loop:

```cpp
while (distance > 10) {
  driveForward();
  distance = readSensor();
}
```

Keep driving while there's more than 10 cm ahead. The moment the sensor reads less, stop.

Notice the second line inside the braces. It's easy to forget, and forgetting it is fatal: if you never re-read the sensor, `distance` holds its old value forever, the condition never becomes false, and your robot drives into the wall at full speed while the loop happily runs a million times a second.

A `while` loop that can never end is called an **infinite loop**. Before you write one, ask the question that prevents it: *what, inside this loop, will eventually make the condition false?* If you can't answer, the loop isn't finished yet.
