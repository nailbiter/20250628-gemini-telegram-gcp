# 20250628-gemini-telegram-gcp

## asyncio primer
Of course. Here is a crash course on how to use `async` functions in Python, focusing on the core concepts you'll need.

### The Core Idea: Cooperative Multitasking 💡

Imagine a chef in a kitchen.

  * **Synchronous Chef:** Makes one dish at a time. They start the pasta, wait for the water to boil, cook it, drain it, make the sauce, and then finally serve it. The kitchen is idle while they wait for the water to boil.
  * **Asynchronous Chef:** Starts the pasta water boiling (`await water.boil()`). While waiting, they don't just stand there. They start chopping vegetables for the sauce (`await veggies.chop()`). When the water boils, the event loop notifies them, they add the pasta, and while it cooks, they finish the sauce.

**`asyncio` in Python is like the asynchronous chef.** It allows your program to handle long waiting periods (like network requests, file I/O, or database calls) by working on other tasks instead of just waiting. This makes your program much more efficient.

-----

### The 3 Magic Keywords

You only need to know three main things to get started.

#### 1\. `async def`: Defining a "Coroutine"

This creates a special kind of function called a **coroutine**. It's a function that can be paused and resumed.

```python
async def get_data_from_server():
    print("Starting to fetch data...")
    # a network request is slow, so we can 'await' it
    await asyncio.sleep(2) # Simulates a 2-second network call
    print("Finished fetching data.")
    return {"data": 123}
```

When you call `get_data_from_server()`, it **doesn't run immediately**. It returns a coroutine object, which is like a recipe that hasn't been cooked yet.

#### 2\. `await`: Pausing and Waiting

The `await` keyword is used **inside an `async def` function**. It tells the program: "This part might take a while. Pause this function here, go do other work if you can, and come back when it's done."

You can only use `await` on other `async` functions or on objects that are "awaitable".

```python
# Inside another async function:
async def process():
    result = await get_data_from_server() # Pauses process() until get_data_from_server() is complete
    print(result)
```

**Rule \#1:** You can **only** use `await` inside a function defined with `async def`.

#### 3\. `asyncio.run()`: Starting the Engine

This is the bridge from the normal, synchronous world to the asynchronous world. `asyncio.run()` takes a coroutine object, starts up the `asyncio` engine (the "event loop"), runs your function until it's complete, and then shuts the engine down.

You use this **once** at the top level of your application to kick everything off.

```python
import asyncio

async def main():
    print("This is my main async function.")
    await asyncio.sleep(1)
    print("Finished.")

# This is how you run it from a regular script.
if __name__ == "__main__":
    asyncio.run(main())
```

-----

### Running Things Concurrently (The Real Power)

This is the most important concept. If you just `await` functions one after another in a loop, you're not getting any concurrency—it's still sequential.

#### The Sequential Way (Slow)

This runs `f(0)`, waits for it to finish, then runs `f(1)`, waits, and so on.

```python
async def main_sequential():
    for i in range(3):
        # This is NOT concurrent.
        await some_async_function(i)
```

#### The Concurrent Way with `asyncio.gather()` (Fast)

To run things at the same time, you create "tasks" and then "gather" them.

1.  **Create Tasks:** Wrap your coroutine calls in `asyncio.create_task()`. This immediately schedules them to run on the event loop.
2.  **Gather Results:** Use `await asyncio.gather()` to wait for all the scheduled tasks to finish.

<!-- end list -->

```python
import asyncio
import time

async def my_task(name, delay):
    print(f"Task '{name}' started.")
    await asyncio.sleep(delay)
    print(f"Task '{name}' finished after {delay} second(s).")

async def main_concurrent():
    start_time = time.time()

    # Schedule all tasks to run without waiting for each one
    tasks = [
        asyncio.create_task(my_task("A", 1)),
        asyncio.create_task(my_task("B", 2)),
        asyncio.create_task(my_task("C", 1))
    ]

    # Now, wait for all of them to complete
    await asyncio.gather(*tasks)

    end_time = time.time()
    print(f"All tasks finished in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(main_concurrent())

# --- EXPECTED OUTPUT ---
# Task 'A' started.
# Task 'B' started.
# Task 'C' started.
# Task 'A' finished after 1 second(s).
# Task 'C' finished after 1 second(s).
# Task 'B' finished after 2 second(s).
# All tasks finished in 2.01 seconds.
```

Notice the total time was \~2 seconds (the duration of the longest task), not 4 seconds (1 + 2 + 1). This is the power of `asyncio`.

### Key Rules to Remember

1.  An `async def` function returns a **coroutine**, not its result.
2.  You must use `await` to get the result of a coroutine.
3.  You can only use `await` inside another `async def` function.
4.  To start the whole process from a normal script, use `asyncio.run()`.
5.  To run coroutines **concurrently**, use `asyncio.gather()` with `asyncio.create_task()`.
