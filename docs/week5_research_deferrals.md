# Week 5 Research Deferrals

Week 5 implements scheduling and allocation for simulated drones only.

Recorded caveats and deferrals:

- The task-allocation review supports comparing algorithms under common metrics, but its narrative and extracted tables conflict about which algorithm is consistently best. Shepherd-AI therefore reports only the measured result of the current synthetic example and does not generalize it.
- Route optimization is not implemented in Week 5.
- Safety validation is not implemented in Week 5.
- Mission execution is not implemented in Week 5.
- The implemented strategies are deterministic baselines and do not prove global optimality.

These limits are intentional so the scheduler remains separate from Week 6 vision, Week 7 safety, and later end-to-end integration work.
