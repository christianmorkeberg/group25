from pathlib import Path
import json
import gurobipy as gp
from gurobipy import GRB, quicksum
class OptModel:
    pass 

def ensure_list(d, key, num_hours):
    v = d.get(key)
    if v is None:
        raise KeyError(f"Missing required data '{key}' in JSON")
    if isinstance(v, list):
        if len(v) != num_hours:
            raise ValueError(f"Length of list for '{key}' must be {num_hours}")
        return v
    else:
        return [v] * num_hours

def build_and_solve(data, debug=True):

    num_hours = len(data.DER_production[0].get("hourly_profile_ratio", [1]*24))
    T = list(range(num_hours))

    P_pv = ensure_list(data.DER_production[0], "hourly_profile_ratio", num_hours)
    phi_imp = ensure_list(data.bus_params[0], "import_tariff_DKK/kWh", num_hours)
    phi_exp = ensure_list(data.bus_params[0], "export_tariff_DKK/kWh", num_hours)
    da_price = ensure_list(data.bus_params[0], "energy_price_DKK_per_kWh", num_hours)

    P_total = data.usage_preference[0]["load_preferences"][0]["min_total_energy_per_day_hour_equivalent"]

    P_down_max = ensure_list(data.bus_params[0], "max_import_kW", num_hours)
    P_up_max   = ensure_list(data.bus_params[0], "max_export_kW", num_hours)
    P_L_max    = ensure_list(data.appliance_params["load"][0], "max_load_kWh_per_hour", num_hours)

    if debug:
        print("=== DATA CHECK ===")
        print("Hours:", num_hours)
        print("Total requested load:", P_total)
        print("Sum PV capacity:", sum(P_pv))
        print("=================\n")

    m = gp.Model("pv_grid_profit_max")
    m.setParam("OutputFlag", 1)

    p_import = {}
    p_export = {}
    p_load = {}
    p_pv_actual = {}
    y = {}
    M = [max(P_down_max[t], P_up_max[t]) for t in T]

    for t in T:
        p_import[t] = m.addVar(lb=0.0, ub=P_down_max[t], name=f"p_import_{t}")
        p_export[t] = m.addVar(lb=0.0, ub=P_up_max[t], name=f"p_export_{t}")
        p_load[t] = m.addVar(lb=0.0, ub=P_L_max[t], name=f"p_load_{t}")
        p_pv_actual[t] = m.addVar(lb=0.0, ub=P_pv[t], name=f"p_pv_actual_{t}")
        y[t] = m.addVar(vtype=GRB.BINARY, name=f"y_{t}")
        m.addConstr(p_import[t] <= M[t] * y[t])
        m.addConstr(p_export[t] <= M[t] * (1 - y[t]))

    m.update()

    obj_terms = []
    for t in T:
        obj_terms.append((da_price[t] - phi_exp[t]) * p_export[t] - (da_price[t] + phi_imp[t]) * p_import[t])
    m.setObjective(quicksum(obj_terms), GRB.MAXIMIZE)

    m.addConstr(quicksum(p_load[t] for t in T) == P_total, name="total_load")

    for t in T:
        m.addConstr(p_import[t] + p_pv_actual[t] == p_load[t] + p_export[t], name=f"hourly_balance_{t}")

    m.optimize()

    if m.status == GRB.OPTIMAL:
        results = {
            "p_import": [p_import[t].X for t in T],
            "p_export": [p_export[t].X for t in T],
            "p_load": [p_load[t].X for t in T],
            "p_pv_actual": [p_pv_actual[t].X for t in T],
            "y": [y[t].X for t in T],
        }
        total_profit = m.objVal
        print("\n=== OPTIMIZATION RESULTS ===")
        for key, values in results.items():
            print(f"{key}: {values}")
        print(f"Total Profit: {total_profit:.2f} DKK")
        print("============================\n")
        return results, total_profit

# Example usage:
# with open("data.json") as f:
#     data = json.load(f)
# build_and_solve(data)
