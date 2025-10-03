import gurobipy as gp
from gurobipy import GRB, quicksum

# Utility function: ensures that a parameter (scalar or list) is returned as a list of hourly values.
# This is important for time-series modeling in energy systems, where some parameters may be constant or vary by hour.
def to_list(v, num_hours,scale=1.0):
    if isinstance(v, list):
        return [vi * scale for vi in v]
    else:
        if v or v==0:
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
    
    def get_storage_capacity(self):
        v = self.appliance_params.get("storage",[{}])
        if v:
            v = v[0].get("storage_capacity_kWh",0)
        else:
            v = 0
        return self.scale.get("storage_capacity_scale",1)*v

    def get_max_charging_power(self):
        v = self.appliance_params.get("storage",[{}])
        if v: 
            v = v[0].get("max_charging_power_ratio",0)
        else:
            v = 0
        return self.scale.get("max_charge_power_scale",1)*v
    
    def get_max_discharging_power(self):
        v = self.appliance_params.get("storage",[{}])
        if v: 
            v=v[0].get("max_discharging_power_ratio",0)
        else:
            v = 0
        return self.scale.get("max_discharge_power_scale",1)*v
    
    def get_charging_efficiency(self):
        v = self.appliance_params.get("storage")
        
        if v: 
            v = v[0].get("charging_efficiency",1)
        else:
            v = 1
        return v
    
    def get_discharging_efficiency(self):
        v = self.appliance_params.get("storage")
        if v:
            v = v[0].get("discharging_efficiency", 1)
        else:
            v = 1
        return v

    def get_initial_soc(self):
        v = self.usage_preference[0].get("storage_preferences")
        if v:
            v = v[0].get("initial_soc_ratio", 0)
        else:
            v = 0
        return self.scale.get("initial_soc_ratio", 1) * v

    def get_minimum_soc(self):
        v = self.usage_preference[0].get("storage_preferences")
        if v:
            v = v[0].get("minimum_soc_ratio", 0)
        else:
            v = 0
        return self.scale.get("soc_min", 1) * v

    def get_final_soc(self):
        v = self.usage_preference[0].get("storage_preferences")
        if v:
            v = v[0].get("final_soc_ratio", 0)
        else:
            v = 0
        return self.scale.get("final_soc_ratio", 1) * v


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
        return to_list(v, num_hours,self.scale.get("export_tariff_scale",.10))

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
        P_bat_cap = self.consumer.get_storage_capacity()
        P_bat_ch_max = self.consumer.get_max_charging_power()
        P_bat_dis_max = self.consumer.get_max_discharging_power()
        P_bat_ch_eff = self.consumer.get_charging_efficiency()
        P_bat_dis_eff = self.consumer.get_discharging_efficiency()

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
            VARIABLES += [f"p_import_{t}", f"p_export_{t}", f"p_load_{t}", f"p_pv_actual_{t}", f"y_{t}",f"z_{t}",
                          f"p_bat_charge_{t}", f"p_bat_discharge_{t}", f"soc_{t}"]

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
            variables[f"z_{t}"]           = model.addVar(vtype=GRB.BINARY, name=f"z_{t}")
            # Battery variables

            variables[f"p_bat_charge_{t}"]    = model.addVar(lb=0, ub=P_bat_ch_max, name=f"p_bat_charge_{t}")
            variables[f"p_bat_discharge_{t}"] = model.addVar(lb=0, ub=P_bat_dis_max, name=f"p_bat_discharge_{t}")
            variables[f"soc_{t}"]             = model.addVar(lb=0, ub=P_bat_cap,      name=f"soc_{t}")



        # Objective
        if question == "question_1a":
            # Maximize profit
            for t in T:
                objective_coeff[f"p_export_{t}"] = (da_price[t] - phi_exp[t])
                objective_coeff[f"p_import_{t}"] = -(da_price[t] + phi_imp[t])
            objective = quicksum(objective_coeff.get(v, 0) * variables[v] for v in VARIABLES)
            model.setObjective(objective, GRB.MAXIMIZE)

        elif question == "question_1b" or question == "question_1c":
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

            # Hourly balance. 
            constraints.append(
                model.addLConstr(
                    variables[f"p_import_{t}"]
                    + variables[f"p_pv_actual_{t}"]
                    + variables[f"p_bat_discharge_{t}"],          # battery delivers this much to the bus
                    GRB.EQUAL,
                    variables[f"p_load_{t}"]
                    + variables[f"p_export_{t}"]
                    + variables[f"p_bat_charge_{t}"],              # this amount goes into battery (before storage losses)
                    name=f"balance_{t}"
                )
            )


            # Exclusivity (Big-M logic) - use separate big-M for import/export
            constraints.append(model.addLConstr(variables[f"p_import_{t}"], GRB.LESS_EQUAL, P_down[t] * variables[f"y_{t}"]))
            constraints.append(model.addLConstr(variables[f"p_export_{t}"], GRB.LESS_EQUAL, P_up[t] * (1 - variables[f"y_{t}"])))

            # Battery exclusivity (Big-M logic) - use separate big-M for charge/discharge
            constraints.append(model.addLConstr(variables[f"p_bat_charge_{t}"], GRB.LESS_EQUAL, P_bat_ch_max * variables[f"z_{t}"]))
            constraints.append(model.addLConstr(variables[f"p_bat_discharge_{t}"], GRB.LESS_EQUAL, P_bat_dis_max * (1 - variables[f"z_{t}"])))

            # Constrain SOC for all houes except the last one where SOC bust be over final_soc (see above)
            # Here we include efficiency!
            if t == T[0]:
                # Initial SOC constraint
                initial_soc = self.consumer.get_initial_soc()
                constraints.append(
                    model.addLConstr(variables[f"soc_{t}"], GRB.GREATER_EQUAL, initial_soc * P_bat_cap, name="soc_init")
                )
            elif t != T[-1]:
                constraints.append(
                    model.addLConstr(
                        variables[f"soc_{t+1}"],
                        GRB.EQUAL,
                        variables[f"soc_{t}"]
                        + P_bat_ch_eff * variables[f"p_bat_charge_{t}"]     # energy stored = charge power * eff_ch
                        - (1.0 / P_bat_dis_eff) * variables[f"p_bat_discharge_{t}"],  # soc reduces by delivered / eff_dis
                        name=f"soc_update_{t}"
                    )
                )
            else:
                final_soc = self.consumer.get_final_soc()
                constraints.append(
                    model.addLConstr(variables[f"soc_{t}"], GRB.GREATER_EQUAL, final_soc * P_bat_cap, name="soc_end_min")
                )


        # initial_soc = self.consumer.get_initial_soc() * P_bat_cap
        # if question in ["question_1c"]:
        #     weight = 1e-3  # small so it doesn't block discharging
        #     model.setObjective(
        #         model.getObjective() + weight * (variables["soc_0"] - initial_soc) * (variables["soc_0"] - initial_soc)
        #     )


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