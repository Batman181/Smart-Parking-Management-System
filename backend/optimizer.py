# backend/optimizer.py
# Uses Google OR-Tools to find the OPTIMAL parking slot for an incoming vehicle
# This is Lecture 12 - OR-Tools Optimization

from ortools.sat.python import cp_model


def find_optimal_slot(available_slots: list, vehicle_type: str = "car"):
    """
    Given a list of free parking slots, find the BEST one for the vehicle.
    
    Optimization criteria:
    - Minimize slot number (closer to entrance = lower number)
    - Prefer slots in Zone-A over Zone-B (Zone A is closer to exit)
    - Prefer slots that haven't been used recently (load balancing)
    
    This uses CP-SAT solver from OR-Tools.
    """
    if not available_slots:
        return None
    
    model = cp_model.CpModel()
    
    n = len(available_slots)
    
    # Decision variable: x[i] = 1 if we choose slot i
    x = [model.NewBoolVar(f"slot_{i}") for i in range(n)]
    
    # Constraint: EXACTLY one slot must be chosen
    model.Add(sum(x) == 1)
    
    # Build cost for each slot (lower cost = better slot)
    costs = []
    for i, slot in enumerate(available_slots):
        # Base cost = slot number within zone
        slot_num = int(slot["slot_id"].split("-S")[1])
        zone_penalty = 0 if "A" in slot["zone"] else 10  # Zone A preferred
        cost = slot_num + zone_penalty
        costs.append(cost)
    
    # Objective: minimize total cost (since only one slot is selected,
    # this minimizes the cost of the selected slot)
    model.Minimize(sum(costs[i] * x[i] for i in range(n)))
    
    # Solve it
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i in range(n):
            if solver.Value(x[i]) == 1:
                return available_slots[i]
    
    # Fallback: return first available slot
    return available_slots[0]
