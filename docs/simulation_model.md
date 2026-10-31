# Simulation model

Coordinates use SI units: x increases down a straight road; y increases leftward; lane centers are y=0 and y=lane_width (default 3.6 m). Ego and other vehicles are 4.5 m long and 1.8 m wide; pedestrians use a 0.6 m square footprint. Heading is atan2(lateral speed, longitudinal speed), in radians.

The model is a longitudinal double integrator with a damped lateral lane-position servo. It is deliberately simpler than a kinematic bicycle: straight-road following, braking, and lane acceptance are the comparison targets. It does not reproduce tire forces, steering geometry, curves, or friction circles. Heading is diagnostic; collision boxes stay axis-aligned. Do not describe it as a physically complete vehicle model.

## Update rules

At each fixed dt (default 0.05 s):

1. Observe current ego and visible actor states, computing footprint clearances and closing velocities.
2. Controller chooses longitudinal acceleration and a target lane.
3. Saturate requested acceleration to [-8, 2.5] m/s², then slew commanded acceleration by at most 10 dt m/s².
4. Update speed with v_next=clip(v+a dt, 0, 40). Integrate x with (v+v_next)dt/2. Record effective acceleration from the actual speed difference.
5. Lateral requested acceleration is clip(1.5(y_target-y)-2.5 v_y, -1.5, 1.5). Slew by 3 dt, constrain lateral speed to ±1.2 m/s, then integrate y. The ego center stays between -0.5 and lane_width+0.5. Lane changing at rest is disabled.
6. Integrate scripted surrounding traffic and pedestrians over the same interval.
7. Check swept collisions, update metrics, record telemetry, and stop on collision, destination passage, or duration.

At speed saturation or a complete stop, effective acceleration can change faster than the requested jerk bound. Lateral stop/speed/road clipping similarly introduces discontinuities. Reports intentionally record those actual accelerations and jerks rather than hiding them. There is no steering actuator in this model; lateral acceleration/speed/jerk constraints stand in for it. Strict steering/curvature and jerk feasibility at stops require a more complete planner and remain limitations.

## Collision and clearance

For two footprints, collision occurs when |dx| <= (length_ego+length_actor)/2 and |dy| <= (width_ego+width_actor)/2. Swept collision uses relative motion over the timestep: intersect the allowable entry/exit intervals on both axes with [0,1]. Thus fast crossings cannot jump through a footprint between samples. Actor paths are approximated linearly within dt. Clearance is Euclidean distance between the disjoint axis-aligned rectangles; overlap has zero clearance. Simulation stops at the end of the first colliding interval, so reported time/distance have dt resolution.

TTC uses longitudinal footprint gap / closing speed only for a front vehicle overlapping the ego lateral corridor. Nonclosing traffic yields infinity, overlap zero. It is not a prediction under acceleration and does not represent lateral crossing TTC. Pedestrian near misses instead appear through physical separation. TTC values are capped only for features and aggregate/clustering calculations, with caps disclosed.

## Scenarios and observability

Eight equal strata: steady following; sudden lead braking; stop/go (lead brakes, then accelerates after three seconds); delayed stationary obstacle; pedestrian crossing; occluded pedestrian; slow-lead lane opportunity; unsafe merge with fast rear traffic.

Initial ego speed U(8,28) m/s, target U(max(15,ego),32), ordinary following gap U(12,85) m, lead U(4,25) m/s, brake onset U(1,6) s, braking -U(2,8) m/s². Static obstacles use zero lead speed and gap U(30,100); obstacle visibility delay U(0.2,1.5) s. Pedestrian cases move the lead 160 m ahead at 25 m/s and sample crossing x U(25,100), initial y U(-8,-2), speed U(0.8,2.2). Occlusion delays visibility U(0.5,2.5) s. Lane opportunities use lead U(4,12). Adjacent rear x U(-90,-20), speed U(12,32), or for unsafe merging U(-30,-6), U(25,40).

Road width, timestep, duration, and destination are scenario fields; defaults are 3.6 m, .05 s, 15 s, and 200 m. All scenarios have two lanes. Lane-change decisions are allowed in all strata when observable gaps permit. No scenario begins with overlapping footprints, but some randomized states are difficult or unavoidable. Invalid bounds are rejected. Pedestrian ETA is estimated from currently observed lateral position and known current walking speed, not future crossing timing. Physical hidden actors still collide before detection. No random noise is sampled inside simulation: replay is deterministic for fixed input/toolchain.