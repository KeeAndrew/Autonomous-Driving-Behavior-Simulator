# Controller design

All controllers share observations and actuator constraints. The observation includes ego/target speed, nearest visible front footprint gap/speed, closing speed, TTC, pedestrian longitudinal gap and estimated entry time, adjacent front/rear clearances and rear closing speed, current acceleration, lane and lane safety.

## Baseline

Free-road acceleration is clip(0.7(target-speed), -4, 2.5). Inside headway 3+1.25v, the controller limits acceleration using 0.45(gap-3-1.25v)-0.8 closing_speed. Gaps below 5 m request emergency -8 m/s². Visible pedestrians within 6+v²/8 m and ETA below 3 s request at least -5 m/s² braking. Final commands are clipped to [-8,2.5]. This is a defensible proportional/headway baseline, but not optimized for the entire distribution.

A slow lead within 45 m, closing speed >2 m/s and no nearby crossing can trigger a change from lane 0 to lane 1. Front clearance must exceed max(15,1.4v), rear clearance max(12,2.5 positive rear-closing-speed). Once accepted, lane changes stay committed to avoid command oscillation. This does not guarantee safety against subsequently changing traffic; no lateral abort trajectory planner is implemented. There is no automatic return lane change.

## Teacher and ML

The teacher uses an IDM-inspired acceleration: 2[1-(v/v_target)^4-((3+max(0,1.6v+v closing/(2 sqrt(6))))/gap)^2]. It combines longer adaptive headway with closing-speed stopping-distance and pedestrian braking terms. This is a privileged *label generator*, but it receives exactly the same observation as all other controllers. It does not read future lead braking or hidden pedestrian state.

The forest learns longitudinal acceleration from teacher trajectories. ML lane logic stays baseline and is explicitly not learned. Training imitates a stronger hand-written policy; it does not discover new driving capability. Runtime nonfinite feature prediction errors fall back to baseline. Missing/corrupt model files fail before evaluation to prevent silent substitution. Trees need no normalization; feature caps and order are identical in C++ and Python.

## Hybrid hypothesis

Hybrid keeps baseline lane logic and adds relative-speed headway 3+1.6v+max(0,v closing/(2 sqrt(6))). It limits acceleration with 0.25(gap-desired)-0.65 closing. When TTC<3 s and traffic is closing, relative stopping acceleration is -closing²/(2 max(gap-3,0.5)). Pedestrian ETA<3.5 s and gap<8+v²/6 adds a current-speed stopping-distance command. Limits still apply through the same actuator model.

These changes are interpretable engineering hypotheses motivated by teacher design and validation differences. The pipeline records actual ML collision wins/losses by scenario category and a source hash before evaluating hybrid on held-out data. This is not an automated rule-discovery system. A nonzero validation advantage supports investigating a behavior, but does not prove that the hybrid modification causes the advantage. The full report can show regressions in braking, progress, comfort, or collisions; report those honestly.

TTC is useful for closing traffic and naturally handles negative/zero relative velocity with infinity. It assumes constant velocity; a lead vehicle about to brake can have infinite current TTC. Relative-speed headway adds margin but still cannot predict unobserved intent. Stopping-distance rules assume achievable deceleration and ignore tire/road variation. Strong braking can increase hard-brake episode counts while reducing collisions; both outcomes must be presented.