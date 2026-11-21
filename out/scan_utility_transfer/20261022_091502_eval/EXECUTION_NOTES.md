# Execution notes

At approximately case 150, found Application.runInBackground=false after the editor reopened. Enabled it through Unity to avoid inactive-window stalls. The runner uses its own elapsed time, seeded RNG and explicit PhysicsScene.Simulate(0.05); it does not use wall-clock delta time for flight dynamics. This changes scheduling, not the frozen model, algorithms, initial conditions or simulation step. Report wall time with this scheduling intervention disclosed.
