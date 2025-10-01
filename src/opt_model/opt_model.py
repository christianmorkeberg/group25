import gurobipy as gp
from gurobipy import GRB, quicksum

# Utility function: ensures that a parameter (scalar or list) is returned as a list of hourly values.
# This is important for time-series modeling in energy systems, where some parameters may be constant or vary by hour.
def to_list(v, num_hours,scale=1.0):
    if isinstance(v, list):
        return [vi * scale for vi in v]
    else:
        if v:
            return [v * scale for _ in range(num_hours)]
        else:
            return [None] * num_hours

# Consumer class: holds load preferences and flexibility
class Consumer:
    """
    Represents a consumer in the energy system.
    - Holds appliance parameters (e.g., max load per hour)
    - Usage preferences (e.g., total daily energy requirement)
    - Can be extended for flexible loads and discomfort calculation (how much the consumer dislikes shifting load from a reference profile)
    """
    def __init__(self, usage_preference, appliance_params, reference_profile=None, flexibility_params=None,scale={}):
        self.usage_preference = usage_preference
        self.appliance_params = appliance_params
        self.reference_profile = reference_profile  # For discomfort calculation
        self.flexibility_params = flexibility_params  # For future flexibility features
        self.scale = scale

    def get_minimum_energy_requirement(self):
        # Returns total required energy for the day (kWh)
        # This is the physical constraint for total consumption by appliances
        min = self.usage_preference[0]["load_preferences"][0]["min_total_energy_per_day_hour_equivalent"]
        if not min:
            return 0.0
        else:
            return min*self.scale.get("load_scale",1.0)
    
    def get_maximum_energy_requirement(self):
        # Returns total required energy for the day (kWh)
        # This is the physical constraint for total consumption by appliances
        max = self.usage_preference[0]["load_preferences"][0]["max_total_energy_per_day_hour_equivalent"]
        if not max:
            return float('inf')
        else:
            return max*self.scale.get("load_scale",1.0)
        
    def get_reference_profile(self, num_hours):
        # Returns the reference load profile (kWh) for discomfort calculation
        v = self.usage_preference[0].get("load_preferences",{})[0].get("hourly_profile_ratio")
        return to_list(v, num_hours, self.scale.get("reference_profile_scale", 1.0))
        

    def get_max_load_per_hour(self, num_hours):
        # Returns max load per hour as a list (kWh)
        # This models the physical limit of appliances at each hour
        v = self.appliance_params["load"][0].get("max_load_kWh_per_hour")
        return to_list(v, num_hours)


# DER class: holds PV and other distributed resources
class DER:
    """
    Represents distributed energy resources in the system (e.g., PV, battery)
    - PV: provides renewable generation profile
    - Battery: (future) enables energy storage and shifting
    """
    def __init__(self, der_production, battery=None,scale ={}):
        self.der_production = der_production
        self.battery = battery  # For future battery integration
        self.scale = scale

    def get_pv_profile(self, num_hours):
        # Returns PV hourly profile (kWh produced each hour)
        # This is the physical renewable generation available to the consumer
        v = self.der_production[0].get("hourly_profile_ratio")
        return to_list(v, num_hours,self.scale.get("pv_scale",1.0))

# Grid class: holds tariffs and grid limits
class Grid:
    """
    Represents grid parameters: tariffs, limits, prices.
    """
    def __init__(self, bus_params,scale={}):
        self.bus_params = bus_params
        self.scale = scale

    """
    Represents the grid connection for the consumer.
    - Tariffs: cost/revenue for importing/exporting electricity
    - Limits: max import/export power per hour
    - Prices: market price for electricity
    """
    def get_import_tariff(self, num_hours):
        # Cost to import electricity from the grid (DKK/kWh)
        v = self.bus_params[0].get("import_tariff_DKK/kWh")
        return to_list(v, num_hours,self.scale.get("import_tariff_scale",1.0))

    def get_export_tariff(self, num_hours):
        # Revenue for exporting electricity to the grid (DKK/kWh)
        v = self.bus_params[0].get("export_tariff_DKK/kWh")
        return to_list(v, num_hours,self.scale.get("export_tariff_scale",1.0))

    def get_energy_price(self, num_hours):
        # Market price for electricity (DKK/kWh)
        v = self.bus_params[0].get("energy_price_DKK_per_kWh")
        return to_list(v, num_hours,self.scale.get("price_scale",1.0))

    def get_max_import(self, num_hours):
        # Maximum power that can be imported from the grid each hour (kW)
        v = self.bus_params[0].get("max_import_kW")
        return to_list(v, num_hours,self.scale.get("max_import_kW",1.0))

    def get_max_export(self, num_hours):
        # Maximum power that can be exported to the grid each hour (kW)
        v = self.bus_params[0].get("max_export_kW")
        return to_list(v, num_hours,self.scale.get("max_export_kW",1.0))

# Main energy system optimization model
class EnergySystemModel:

    def __init__(self, consumer, der, grid):
        self.consumer = consumer
        self.der = der
        self.grid = grid
        self.model = None
        self.results = None

    # def build_and_solve(self, debug=False, question="question_1a"):
    #     # --- Extract all physical parameters from the system ---
    #     # PV production profile: renewable energy available each hour
    #     # Import tariff: cost to buy electricity from the grid
    #     # Export tariff: revenue for selling electricity to the grid
    #     # Day-ahead market price: market value of electricity
    #     # Total energy demand required by appliances (physical constraint)
    #     # Maximum allowed import/export/load per hour (physical grid/appliance limits)
    #     num_hours = len(self.der.get_pv_profile(0)) if self.der.get_pv_profile(0) else 24
    #     T = list(range(num_hours))

    #     P_pv = self.der.get_pv_profile(num_hours)
    #     phi_imp = self.grid.get_import_tariff(num_hours) # Tariff to import from grid
    #     phi_exp = self.grid.get_export_tariff(num_hours) # Tariff to export to grid
    #     da_price = self.grid.get_energy_price(num_hours) # Day-ahead market price

    #     P_min = self.consumer.get_minimum_energy_requirement()
    #     P_max = self.consumer.get_maximum_energy_requirement()
    #     P_down_max = self.grid.get_max_import(num_hours)
    #     P_up_max   = self.grid.get_max_export(num_hours)
    #     P_L_max    = self.consumer.get_max_load_per_hour(num_hours)

    #     if debug:
    #         print("=== DATA CHECK ===")
    #         print("Hours:", num_hours)
    #         print(f"Total requested load between {P_min} and {P_max}",)
    #         print("Sum PV capacity:", sum(P_pv))
    #         print("=================\n")

    #     # --- Build optimization model ---
    #     # Decision variables for each hour:
    #     # p_import: power imported from grid (kWh)
    #     # p_export: power exported to grid (kWh)
    #     # p_load: power consumed by appliances (kWh)
    #     # p_pv_actual: actual PV power used (kWh)
    #     # y: binary, 1=import active, 0=export active (models grid connection mode)
    #     m = gp.Model("pv_grid_profit_max")
    #     m.setParam("OutputFlag", 0) # 1=show solver output, 0=quiet

    #     p_import = {}
    #     p_export = {}
    #     p_load = {}
    #     p_pv_actual = {}
    #     y = {}
    #     for t in T:
    #         p_import[t] = m.addVar(lb=0.0, ub=P_down_max[t], name=f"p_import_{t}") # kWh imported from grid
    #         p_export[t] = m.addVar(lb=0.0, ub=P_up_max[t], name=f"p_export_{t}") # kWh exported to grid
    #         p_load[t] = m.addVar(lb=0.0, ub=P_L_max[t], name=f"p_load_{t}") # kWh consumed by appliances
    #         p_pv_actual[t] = m.addVar(lb=0.0, ub=P_pv[t], name=f"p_pv_actual_{t}") # kWh of PV used
    #         y[t] = m.addVar(vtype=GRB.BINARY, name=f"y_{t}") # Binary variable for import/export mode
    #         # Use separate big-M values for import and export
    #         m.addConstr(p_import[t] <= P_down_max[t] * y[t])
    #         m.addConstr(p_export[t] <= P_up_max[t] * (1 - y[t]))

    #     m.update()

    #     # --- Objective selection ---
    #     if question == "question_1a":
    #         # Maximize profit from trading electricity (original)
    #         obj_terms = []
    #         for t in T:
    #             obj_terms.append((da_price[t] - phi_exp[t]) * p_export[t] - (da_price[t] + phi_imp[t]) * p_import[t])
    #         m.setObjective(quicksum(obj_terms), GRB.MAXIMIZE)

    #     elif question == "question_1b":
    #         # Minimise cost + discomfort
    #         # Cost (negative profit)
    #         cost_terms = [-1*((da_price[t] - phi_exp[t]) * p_export[t] - (da_price[t] + phi_imp[t]) * p_import[t]) for t in T]
    #         # Discomfort: sum of squared deviation from reference profile
    #         reference_profile = self.consumer.get_reference_profile(num_hours)
    #         # Try to get discomfort_cost_per_kWh from consumer, else default to 1.0
    #         discomfort_cost_per_kWh = getattr(self.consumer, 'discomfort_cost_per_kWh', 1.0)
    #         discomfort_terms = [ (p_load[t] - reference_profile[t]) * (p_load[t] - reference_profile[t]) for t in T ]
    #         m.setObjective(quicksum(cost_terms) + discomfort_cost_per_kWh * quicksum(discomfort_terms), GRB.MINIMIZE)
    #     else:
    #         raise ValueError(f"Unknown objective: {question}")

    #     # --- Constraints ---
        
    #     # Total appliance load over all hours must meet required energy demand interval
    #     m.addConstr(quicksum(p_load[t] for t in T) >= P_min, name="total_load_min")
    #     m.addConstr(quicksum(p_load[t] for t in T) <= P_max, name="total_load_max")
    #     # Physical energy balance: for each hour, imported + PV = load + exported (always enforced)
    #     for t in T:
    #         m.addConstr(p_import[t] + p_pv_actual[t] == p_load[t] + p_export[t], name=f"hourly_balance_{t}")

    #     # --- Solve the model ---
    #     m.optimize()

    #     # --- Output results if optimal solution found ---
    #     if m.status == GRB.OPTIMAL:
    #         p_import_list = [p_import[t].X for t in T]
    #         p_export_list = [p_export[t].X for t in T]
    #         p_load_list = [p_load[t].X for t in T]
    #         p_pv_actual_list = [p_pv_actual[t].X for t in T]
    #         y_list = [y[t].X for t in T]
    #         curtailment_list = [P_pv[t] - p_pv_actual_list[t] for t in T]
    #         # Calculate cost and discomfort if possible
    #         cost = None
    #         discomfort = None
    #         if hasattr(self, 'question') and self.question == "question_1b":
    #             # Recompute cost and discomfort for reporting
    #             cost = sum([-1*((da_price[t] - phi_exp[t]) * p_export_list[t] - (da_price[t] + phi_imp[t]) * p_import_list[t]) for t in T])
    #             try:
    #                 reference_profile = self.consumer.get_reference_profile(num_hours)
    #                 discomfort = sum([(p_load_list[t] - reference_profile[t])**2 for t in T])
    #             except Exception:
    #                 discomfort = None
    #         self.results = {
    #             "p_import": p_import_list,
    #             "p_export": p_export_list,
    #             "p_load": p_load_list,
    #             "p_pv_actual": p_pv_actual_list,
    #             "curtailment": curtailment_list,
    #             "y": y_list,
    #             "reference_profile": self.consumer.get_reference_profile(num_hours),
    #             "P_pv": P_pv,
    #             "cost": cost,
    #             "discomfort": discomfort
    #         }
    #         self.total_profit = m.objVal
    #     else:
    #         self.results = None
    #         self.total_profit = None
    #     return self.results, getattr(self, 'total_profit', None)




    def build_and_solve_standardized(self, debug=False, question="question_1a"):
        num_hours = len(self.der.get_pv_profile(0)) if self.der.get_pv_profile(0) else 24
        T = list(range(num_hours))

        # Parameters
        P_pv     = self.der.get_pv_profile(num_hours)
        phi_imp  = self.grid.get_import_tariff(num_hours)
        phi_exp  = self.grid.get_export_tariff(num_hours)
        da_price = self.grid.get_energy_price(num_hours)

        P_min    = self.consumer.get_minimum_energy_requirement()
        P_max    = self.consumer.get_maximum_energy_requirement()
        P_down   = self.grid.get_max_import(num_hours)
        P_up     = self.grid.get_max_export(num_hours)
        P_L_max  = self.consumer.get_max_load_per_hour(num_hours)

        if debug:
            print("=== DATA CHECK ===")
            print("Hours:", num_hours)
            print(f"Total requested load between {P_min} and {P_max}")
            print("Sum PV capacity:", sum(P_pv))
            print("=================\n")

        # -----------------------------
        # Standardized formulation
        # -----------------------------
        VARIABLES = []
        objective_coeff = {}

        # Define variable names
        for t in T:
            VARIABLES += [f"p_import_{t}", f"p_export_{t}", f"p_load_{t}", f"p_pv_actual_{t}", f"y_{t}"]

        # Create model
        model = gp.Model("pv_grid_profit_max")
        model.setParam("OutputFlag", 0)

        # Add variables with bounds
        variables = {}
        for t in T:
            variables[f"p_import_{t}"]    = model.addVar(lb=0, ub=P_down[t], name=f"p_import_{t}")
            variables[f"p_export_{t}"]    = model.addVar(lb=0, ub=P_up[t],   name=f"p_export_{t}")
            variables[f"p_load_{t}"]      = model.addVar(lb=0, ub=P_L_max[t],name=f"p_load_{t}")
            variables[f"p_pv_actual_{t}"] = model.addVar(lb=0, ub=P_pv[t],   name=f"p_pv_actual_{t}")
            variables[f"y_{t}"]           = model.addVar(vtype=GRB.BINARY, name=f"y_{t}")

        # Objective
        if question == "question_1a":
            # Maximize profit
            for t in T:
                objective_coeff[f"p_export_{t}"] = (da_price[t] - phi_exp[t])
                objective_coeff[f"p_import_{t}"] = -(da_price[t] + phi_imp[t])
            objective = quicksum(objective_coeff.get(v, 0) * variables[v] for v in VARIABLES)
            model.setObjective(objective, GRB.MAXIMIZE)

        elif question == "question_1b":
            # Minimize cost + discomfort
            reference_profile = self.consumer.get_reference_profile(num_hours)
            discomfort_cost_per_kWh = getattr(self.consumer, 'discomfort_cost_per_kWh', 1.0)

            cost_terms = quicksum(
                (phi_imp[t] + da_price[t]) * variables[f"p_import_{t}"]
                - (da_price[t] - phi_exp[t]) * variables[f"p_export_{t}"]
                for t in T
            )

            discomfort_terms = quicksum(
                (variables[f"p_load_{t}"] - reference_profile[t]) *
                (variables[f"p_load_{t}"] - reference_profile[t])
                for t in T
            )

            model.setObjective(cost_terms + discomfort_cost_per_kWh * discomfort_terms, GRB.MINIMIZE)

        # -----------------------------
        # Constraints
        # -----------------------------
        constraints = []

        # Energy requirement bounds
        constraints.append(
            model.addLConstr(quicksum(variables[f"p_load_{t}"] for t in T), GRB.GREATER_EQUAL, P_min, name="total_load_min")
        )
        constraints.append(
            model.addLConstr(quicksum(variables[f"p_load_{t}"] for t in T), GRB.LESS_EQUAL, P_max, name="total_load_max")
        )

        # Hourly balance + import/export exclusivity
        for t in T:
            constraints.append(
                model.addLConstr(
                    variables[f"p_import_{t}"] + variables[f"p_pv_actual_{t}"],
                    GRB.EQUAL,
                    variables[f"p_load_{t}"] + variables[f"p_export_{t}"],
                    name=f"balance_{t}"
                )
            )
            # Exclusivity (Big-M logic) - use separate big-M for import/export
            constraints.append(model.addLConstr(variables[f"p_import_{t}"], GRB.LESS_EQUAL, P_down[t] * variables[f"y_{t}"]))
            constraints.append(model.addLConstr(variables[f"p_export_{t}"], GRB.LESS_EQUAL, P_up[t] * (1 - variables[f"y_{t}"])))

        # -----------------------------
        # Solve
        # -----------------------------
        model.optimize()

        if model.status == GRB.OPTIMAL:
            results = {v: variables[v].X for v in VARIABLES}
            self.results = results
            self.total_profit = model.objVal
            return results, model.objVal
        else:
            self.results = None
            self.total_profit = None
            return None, None