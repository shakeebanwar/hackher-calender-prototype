import streamlit as st
import math
import pandas as pd
from datetime import datetime, timedelta, date

# ==========================================
# CORE LOGIC CLASSES
# ==========================================

class CycleHistoryCalculator:
    def validate_single_entry(self, start_date: datetime, end_date: datetime) -> int:
        duration = (end_date - start_date).days + 1
        if duration < 3:
            raise ValueError(f"Bleed duration {duration} days is too short (Min 3 days).")
        if duration > 10:
            raise ValueError(f"Bleed duration {duration} days is too long (Max 10 days).")
        return duration

    def process_history(self, history_data):
        if not history_data:
            return None
        history_data.sort(key=lambda x: x['start'])
        bleed_durations = []
        for entry in history_data:
            d = self.validate_single_entry(entry['start'], entry['end'])
            bleed_durations.append(d)
        cycle_gaps = []
        if len(history_data) > 1:
            for i in range(len(history_data) - 1):
                gap = (history_data[i+1]['start'] - history_data[i]['start']).days
                cycle_gaps.append(gap)
        
        # Bleed Logic (Round Down)
        if len(bleed_durations) == 1:
            final_bleed_avg = bleed_durations[0]
        else:
            avg_raw = sum(bleed_durations) / len(bleed_durations)
            final_bleed_avg = math.floor(avg_raw)

        # Cycle Logic (Round Up)
        if not cycle_gaps:
            final_cycle_avg = 28
        else:
            avg_cycle_raw = sum(cycle_gaps) / len(cycle_gaps)
            final_cycle_avg = math.ceil(avg_cycle_raw)

        return {
            "bleed_avg": final_bleed_avg,
            "cycle_avg": final_cycle_avg,
            "total_cycles": len(history_data),
            "cycle_gaps": cycle_gaps
        }

class OvulationPredictor:
    def __init__(self):
        self.CRASH_1 = 2
        self.NURTURE = 6
        self.CRASH_2 = 3

    def predict(self, start_date_obj: date, raw_bleed: float, raw_cycle: float):
        # 1. Rounding
        bleed = math.floor(raw_bleed)
        cycle = math.ceil(raw_cycle)

        # 2. Basic Validation
        if not (3 <= bleed <= 10):
            raise ValueError(f"Bleed days must be 3-10. (Rounded value: {bleed})")
        if not (21 <= cycle <= 35):
            raise ValueError(f"Cycle length must be 21-35. (Rounded value: {cycle})")

        # 3. Complex Validation
        max_map = {21:5, 22:6, 23:7, 24:8, 25:9}
        max_allowed = max_map.get(cycle, 10) 
        if bleed > max_allowed:
            raise ValueError(f"For a {cycle}-day cycle, max bleed is {max_allowed}. You have {bleed}.")

        # 4. Math Formulas & Timeline Calculation
        constants_sum = self.CRASH_1 + self.NURTURE + self.CRASH_2
        power_week = cycle - (bleed + constants_sum)
        
        # --- Timeline Generation Logic ---
        timeline = []
        current_date = start_date_obj

        # Phase 1: Bleed
        bleed_end = current_date + timedelta(days=bleed - 1)
        timeline.append({"Phase": "🩸 Bleed Days", "Start": current_date, "End": bleed_end, "Days": bleed, "Color": "#ffcccc"})
        current_date = bleed_end + timedelta(days=1)

        # Phase 2: Power Week
        pw_end = current_date + timedelta(days=power_week - 1)
        timeline.append({"Phase": "⚡ Power Week", "Start": current_date, "End": pw_end, "Days": power_week, "Color": "#ffffcc"})
        current_date = pw_end + timedelta(days=1)

        # Phase 3: Crash 1
        c1_end = current_date + timedelta(days=self.CRASH_1 - 1)
        timeline.append({"Phase": "📉 Crash #1", "Start": current_date, "End": c1_end, "Days": self.CRASH_1, "Color": "#e6e6e6"})
        current_date = c1_end + timedelta(days=1)

        # Phase 4: Nurture
        nur_end = current_date + timedelta(days=self.NURTURE - 1)
        timeline.append({"Phase": "🌱 Nurture", "Start": current_date, "End": nur_end, "Days": self.NURTURE, "Color": "#ccffcc"})
        current_date = nur_end + timedelta(days=1)

        # Phase 5: Crash 2
        c2_end = current_date + timedelta(days=self.CRASH_2 - 1)
        timeline.append({"Phase": "📉 Crash #2", "Start": current_date, "End": c2_end, "Days": self.CRASH_2, "Color": "#e6e6e6"})

        # --- Fertile Window Calculation ---
        main_ovulation_day_num = (bleed + power_week) - 2
        main_date = start_date_obj + timedelta(days=main_ovulation_day_num - 1)
        
        baby_days = []
        for i in range(4, 0, -1):
            baby_days.append(main_date - timedelta(days=i))
        baby_days.append(main_date)
        baby_days.append(main_date + timedelta(days=1))

        return {
            "rounded_bleed": bleed,
            "rounded_cycle": cycle,
            "power_week": power_week,
            "main_date": main_date,
            "baby_days": baby_days,
            "timeline": timeline
        }

# ==========================================
# UI CONFIGURATION
# ==========================================

st.set_page_config(page_title="Cycle Algorithms", page_icon="🩸", layout="wide")

# --- SIDEBAR MENU ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Choose Algorithm:", ["Algo #01: History Calculation", "Algo #02: Future Prediction"])
st.sidebar.divider()
st.sidebar.info("Use the menu above to switch between History Calculator and Future Prediction.")

# --- PAGE 1: ALGO #01 ---
if app_mode == "Algo #01: History Calculation":
    st.title("📜 Algo #01: History & Averages")
    st.markdown("---")
    
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. Add Past Cycle")
        with st.form("add_cycle_form"):
            h_start = st.date_input("Bleed Start Date", value=date.today())
            h_end = st.date_input("Bleed End Date", value=date.today() + timedelta(days=4))
            submitted = st.form_submit_button("Add to History")
            
            if submitted:
                calc_check = CycleHistoryCalculator()
                try:
                    s_dt = datetime.combine(h_start, datetime.min.time())
                    e_dt = datetime.combine(h_end, datetime.min.time())
                    calc_check.validate_single_entry(s_dt, e_dt)
                    st.session_state['history'].append({'start': s_dt, 'end': e_dt})
                    st.success("Added!")
                except ValueError as e:
                    st.error(str(e))

        if st.button("Reset History"):
            st.session_state['history'] = []
            st.rerun()

    with col2:
        st.subheader("2. Results")
        if st.session_state['history']:
            display_data = []
            for i, item in enumerate(st.session_state['history']):
                dur = (item['end'] - item['start']).days + 1
                display_data.append({
                    "Cycle #": i+1,
                    "Start": item['start'].strftime("%Y-%m-%d"),
                    "End": item['end'].strftime("%Y-%m-%d"),
                    "Duration": f"{dur} days"
                })
            st.dataframe(pd.DataFrame(display_data), use_container_width=True)

            algo1 = CycleHistoryCalculator()
            try:
                res = algo1.process_history(st.session_state['history'])
                st.success("### Final Averages")
                m1, m2 = st.columns(2)
                m1.metric("Avg Bleed (Round Down)", f"{res['bleed_avg']} Days")
                m2.metric("Avg Cycle (Round Up)", f"{res['cycle_avg']} Days")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please add at least one cycle entry on the left.")

# --- PAGE 2: ALGO #02 ---
elif app_mode == "Algo #02: Future Prediction":
    st.title("🔮 Algo #02: Prediction & Timeline")
    st.markdown("---")
    
    st.write("Enter your data below to see the **Full Cycle Roadmap**.")

    c1, c2, c3 = st.columns(3)
    with c1:
        p_start = st.date_input("Cycle Start Date (Day 1)", value=date.today())
    with c2:
        p_bleed = st.number_input("Bleed Duration", min_value=0.0, max_value=15.0, value=5.0, step=0.1)
    with c3:
        p_cycle = st.number_input("Cycle Duration", min_value=0.0, max_value=50.0, value=28.0, step=0.1)

    if st.button("Generate Cycle Roadmap", type="primary"):
        algo2 = OvulationPredictor()
        try:
            res = algo2.predict(p_start, p_bleed, p_cycle)
            
            # --- SECTION 1: KEY STATS ---
            st.divider()
            st.subheader("1. Key Calculations")
            k1, k2, k3 = st.columns(3)
            k1.info(f"**Bleed:** {res['rounded_bleed']} Days")
            k2.info(f"**Power Week:** {res['power_week']} Days")
            k3.info(f"**Total Cycle:** {res['rounded_cycle']} Days")

            # --- SECTION 2: FULL TIMELINE (NEW) ---
            st.subheader("2. 📅 Full Cycle Timeline")
            
            # Prepare data for display
            timeline_data = []
            for item in res['timeline']:
                timeline_data.append({
                    "Phase Name": item["Phase"],
                    "Start Date": item["Start"].strftime("%d %b %Y"),
                    "End Date": item["End"].strftime("%d %b %Y"),
                    "Duration": f"{item['Days']} Days"
                })
            
            # Show as a styled Table
            df_timeline = pd.DataFrame(timeline_data)
            st.table(df_timeline)

            # --- SECTION 3: FERTILE WINDOW ---
            st.subheader("3. ❤️ Fertile Window (Baby Days)")
            
            cols = st.columns(6)
            baby_dates_fmt = [d.strftime("%d %b") for d in res['baby_days']]
            
            for i, date_str in enumerate(baby_dates_fmt):
                with cols[i]:
                    if i == 4: # Main Day
                        st.error(f"{date_str}\n(Main)")
                    else:
                        st.success(f"{date_str}")
            
            st.caption("Note: Main Ovulation Day is highlighted in RED.")

        except ValueError as e:
            st.error(f"❌ **VALIDATION FAILED:** {str(e)}")
            st.markdown("""
            **Rules:**
            * Bleed: 3-10 days
            * Cycle: 21-35 days
            * Max Bleed logic applies based on cycle length.
            """)