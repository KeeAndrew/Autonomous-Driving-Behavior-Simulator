# Interview preparation

## Thirty-second explanation

I built a C++20 simulator to compare explicit driving rules with a random forest trained to imitate a stronger teacher. It runs deterministic following, braking, pedestrian, and lane-change scenarios under shared perception and dynamics. Python pairs behavioral disagreements, clusters them with K-Means and DBSCAN, and reports safety, braking, progress, and comfort with confidence intervals. I also tested interpretable relative-speed and TTC rules as a hybrid controller. I report the actual measurements, including regressions, rather than assume that learning improves safety.

## Two-minute walkthrough

The project separates simulation, control, and evaluation. Each fixed timestep constructs the same current-state observation for every controller. The ego uses constrained longitudinal acceleration and a damped lateral lane servo. Surrounding vehicles follow prescribed scripts, pedestrians move laterally, and swept rectangle collision detection prevents actors from tunneling through one another between timesteps.

The baseline uses speed-error control and a fixed time-headway rule. An explicit IDM-inspired teacher uses relative-speed headway and stopping-distance logic. I generate teacher demonstrations on independent training scenarios, train a 32-tree acceleration regressor in Python, and export its nodes for C++ inference. A parity test checks both ordinary inputs and split boundaries because scikit-learn casts features to float32.

Before held-out evaluation, baseline and ML run on validation scenarios. I inspect their paired disagreements and freeze the interpretable hybrid hypothesis. Evaluation uses independent seeds and the same scenario rows for all three controllers. Divergence means a predeclared command, trajectory, lane, or collision disagreement. Standardized clustering reveals recurring combinations, and category proportions help interpret them without assuming clusters match scenario names. A paired bootstrap resamples scenarios, preserving shared difficulty.

The most important limitation is simulation realism. This is synthetic imitation learning on a simplified straight road, with no real sensors or tire dynamics. It demonstrates controlled experimentation and engineering, not readiness to drive a real car. For exact counts and improvements I would quote only `verified_results.md` and the generated report.

## Detailed technical explanation

The state contains x/y position, longitudinal/lateral speed and acceleration, and diagnostic heading. Requested longitudinal acceleration is amplitude- and slew-limited, then speed is saturated and position integrated trapezoidally. Actual acceleration and jerk are measured after saturation, making stop transients visible. The lateral lane servo limits acceleration/speed/jerk and commits accepted lane changes. It does not model steering geometry; a bicycle model is a justified next extension.

Observation construction handles vehicle dimensions before TTC. The nearest visible front actor in the ego corridor gives gap and lead speed. Closing speed is ego minus lead. TTC is gap/closing only when closing>epsilon; receding or equal-speed pairs use infinity. A lead vehicle can have infinite current TTC and then brake, so a headway margin remains useful. Pedestrian ETA uses current visible position and walking speed. Visibility delay is a simulator mechanism; controllers cannot read its timer or hidden actors.

A stronger teacher provides observable-state acceleration labels. All rows from a scenario stay in one split. The forest is an approximation of that teacher, and the policy can drift into unseen states at runtime. It is not evidence of novel behavior discovered from real driving. Shared baseline lane decisions isolate longitudinal learning. The exported tree topology is validated, input float casts match training, and invalid models fail before an experiment.

Collisions use time intervals of relative rectangle overlap on both axes. Metrics are accumulated on the complete timestep stream; telemetry is sampled only for storage and analysis. Near-miss and hard-braking event counters use rising edges to avoid counting a long episode as many events. Outcome differences remain paired by scenario. Clusters use differences between controllers rather than raw trajectories; they summarize recurring disagreement patterns for investigation. A hybrid converts physically understandable ideas into explicit rules, but the validation evidence is correlational and all gains require held-out confirmation.

## Twenty likely technical questions

1. **Why not CARLA or 3D?** A small 2D engine makes the controller/metric contracts inspectable and deterministic, without graphics/sensor setup overwhelming the experiment. It sacrifices environmental realism and cannot support claims about real perception.

2. **Why C++20 and Python?** C++ owns the time-stepped runtime and makes controller deployment/inference explicit. Python supplies mature training, clustering, and statistical libraries. CSV and a versioned text forest form inspectable interchange contracts.

3. **Why a double integrator instead of a bicycle model?** Straight-road longitudinal decisions are the first target. A lane-position servo permits controlled gap-acceptance comparisons with fewer parameters. Steering feasibility, curvature, tire forces, and road friction are not represented; a bicycle model would be necessary for those questions.

4. **What is deterministic?** Fixed scenario data, current-state controllers, fixed dt, scripted actors, and fixed model mean repeated rollouts on the recorded toolchain return the same outcomes. Dataset generation and training have explicit seeds. Floating point and package versions prevent claiming universal bitwise equality across architectures.

5. **How do you prevent collisions between timesteps from being missed?** Transform ego/actor motion into relative motion, expand actor bounds by ego half dimensions, solve axis entry/exit intervals, and test whether their intersection overlaps [0,1]. This assumes piecewise-linear motion within each step.

6. **What does TTC omit?** Future acceleration, lateral crossings, intent, and hidden obstacles. It is meaningful only for current closing motion. Infinity for nonclosing traffic is correct rather than an arbitrary large physical TTC; caps apply only to finite features/statistics.

7. **Why include vehicle dimensions?** Center distances overestimate usable braking clearance. Subtracting both half lengths yields bumper clearance; lateral overlap uses both half widths. Collision and controller gap definitions therefore agree.

8. **What is the baseline and is it engineered to lose?** It is a conventional target-speed plus proportional headway/closing-speed policy with emergency and pedestrian braking. It is intentionally understandable, not tuned to fail. A stronger optimized rule baseline would be a useful additional comparator and might outperform this ML model.

9. **Where do labels come from?** An explicit IDM-inspired teacher using the same observation as the learner. Labels are current acceleration decisions, not future safety outcomes. This is synthetic behavioral cloning, with its advantages and inherited teacher limitations.

10. **How is leakage prevented?** Scenario-level seeds and ID ranges differ across splits. No evaluation results enter training, no future scripted state enters observation, and scenario kind/time are excluded from features. Held-out evaluation is consumed only after validation evidence and source hash are saved.

11. **Why random forests?** They fit nonlinear stopping/headway logic without feature normalization and can be exported as simple branches/leaves. They are interpretable at the feature-importance level, although many trees remain less transparent than explicit rules. They cannot extrapolate safely beyond the demonstrated state distribution.

12. **How did you validate C++ inference?** Compare exported C++ predictions to the actual fitted scikit-learn model, including held-out feature rows and exact/neighboring split values. Match scikit-learn's float32 input conversion before double-threshold comparisons. A small independent model is also trained/exported in tests.

13. **What is divergence mathematically?** On the common sampled prefix, use RMS command differences and 2D trajectory differences, plus desired-lane disagreement fraction. Predeclared thresholds select a scenario, as does a collision mismatch. One selected row per ID prevents fabricated volume; actual counts can fall below targets.

14. **Why cluster differences rather than all scenarios?** The question is where policies behave differently, not how the entire scenario generator is distributed. Difference vectors highlight disagreements worth investigating. Selection bias is intentional and disclosed; clusters do not estimate prevalence outside the evaluated distribution.

15. **Why both K-Means and DBSCAN?** K-Means supplies compact centroid summaries and an explicit k study. DBSCAN finds density groups and noise without requiring spherical equal-size clusters, but is sensitive to scaling, eps, dimension, and density. Agreement/disagreement between the two is useful evidence about structure.

16. **How are cluster parameters chosen?** Standardize features; record K-Means inertia and silhouettes for k=2..8; choose maximum silhouette. Test DBSCAN eps values from predeclared neighbor-distance quantiles and report min_samples/noise/non-noise silhouette. Semantic scenario labels are used only after clustering for interpretation.

17. **Does hybrid copy the forest?** No. It contains explicit relative-speed headway, TTC, and stopping-distance equations, plus baseline architecture. Validation behavior motivates investigation; the equations are predeclared hypotheses rather than an automatic extraction algorithm or proof of causality.

18. **What counts as one hard brake?** A transition from acceleration>=-4 to acceleration<-4 m/s² starts an event. Consecutive qualifying frames form one episode. A return above threshold followed by braking counts again. Report total events, distance-normalized events, time braking, and collisions together because early crashes truncate opportunity.

19. **Why a paired bootstrap?** Every controller encounters the same scenario difficulty. Resampling scenario IDs together preserves that correlation. One thousand seeded replicates give percentile intervals on mean differences and relative reductions. It does not quantify simulator realism or correct domain shift.

20. **What would you improve next?** Add stronger rule baselines and ablations; use new holdouts for each tuning cycle; add sensor latency/noise and randomized road friction; implement bicycle dynamics and feasible trajectory planning; test multiple actors/curved roads; validate against external datasets/simulators; benchmark runtime and profile memory; add rare-event sampling with correct prevalence weighting.

## Résumé metrics and truthful wording

The original 25% collision / 18% braking reductions and 1,500 divergences are targets, not promises. `docs\verified_results.md` records actual counts and improvements. The report defines all denominators and includes negative changes. Quote held-out scenario count per controller separately from total rollouts; do not count teacher demonstrations as independent evaluation. A divergence is a unique selected scenario, not a telemetry row. A collision reduction is relative to the measured baseline, and an undefined denominator must never be presented as a percentage.

Do not describe synthetic differences as ML-production divergences: there are no production logs. Do not claim the hybrid was learned automatically, the baseline was state of the art, or that clustering establishes causes. A safe initial résumé statement is: “Implemented a C++20 autonomous-driving behavior simulator with Python random-forest imitation learning, native C++ inference parity checks, and paired K-Means/DBSCAN behavioral analysis.” Add counts and improvements only from the verified experiment.

## Limitations and tradeoffs to volunteer

Two straight lanes, scripted open-loop traffic, uniform synthetic draws, axis-aligned boxes, a simplified lateral servo, perfect visible measurements, no road friction model, no learned lane policy, no emergency planner with hard safety guarantees, and stop/saturation jerk discontinuities all limit interpretation. Cluster parameter selection is descriptive and silhouette-based, not proof of naturally occurring categories. A single seed family is not sufficient for real-world safety. These are explicit boundaries of the implemented experiment, not reasons to hide negative results.