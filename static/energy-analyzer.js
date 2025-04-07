// Handle Light and Dark Mode
const toggle_display = checkbox => {
    if (checkbox.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.cookie = "theme=dark";
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        document.cookie = "theme=light";
    }
};

let light_mode_enabled = document.cookie.indexOf('theme=dark') !== -1;
let mode_type = light_mode_enabled ? 'dark' : 'light';
document.documentElement.setAttribute('data-theme', mode_type);
document.getElementById("light-switch").checked = light_mode_enabled;

// Map the FIPS code associated to each state on the map to its state abbreviation
const fips_to_state_abbr = {
    'US00': 'US',
    'US01': 'AL',
    'US02': 'AK',
    'US04': 'AZ',
    'US05': 'AR',
    'US06': 'CA',
    'US08': 'CO',
    'US09': 'CT',
    'US10': 'DE',
    'US11': 'DC',
    'US12': 'FL',
    'US13': 'GA',
    'US15': 'HI',
    'US16': 'ID',
    'US17': 'IL',
    'US18': 'IN',
    'US19': 'IA',
    'US20': 'KS',
    'US21': 'KY',
    'US22': 'LA',
    'US23': 'ME',
    'US24': 'MD',
    'US25': 'MA',
    'US26': 'MI',
    'US27': 'MN',
    'US28': 'MS',
    'US29': 'MO',
    'US30': 'MT',
    'US31': 'NE',
    'US32': 'NV',
    'US33': 'NH',
    'US34': 'NJ',
    'US35': 'NM',
    'US36': 'NY',
    'US37': 'NC',
    'US38': 'ND',
    'US39': 'OH',
    'US40': 'OK',
    'US41': 'OR',
    'US42': 'PA',
    'US44': 'RI',
    'US45': 'SC',
    'US46': 'SD',
    'US47': 'TN',
    'US48': 'TX',
    'US49': 'UT',
    'US50': 'VT',
    'US51': 'VA',
    'US53': 'WA',
    'US54': 'WV',
    'US55': 'WI',
    'US56': 'WY'
};

let current_state = 'United States';

const update_state_summaries = (data, id) => {
    data = {
        ...data,
        id
    }
    const element = document.getElementById(id);
    element.innerHTML = '<progress />'
    return fetch(`https://api.jonathan-keys.com/state`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
        .then(res => res.json())
        .then(res => {
            if (res.statusCode === 200) {
                element.innerHTML = res.info;
            } else {
                element.innerHTML = '<em data-tooltip="Bedrock model being used has a 5 request per minute limit">Error</em>'
            }
        })
        .catch(error => {
            element.innerHTML = '<em data-tooltip="Bedrock model being used has a 5 request per minute limit">Error</em>'
        });
}

// Adds the facts about the state to its production and consumption areas
const update_state_facts = (facts, type) => {
    if (facts) {
        document.getElementById(`${type}-non-renewable-data`).innerHTML = build_fact_sheet(facts[type].non_renewable)
        document.getElementById(`${type}-renewable-data`).innerHTML = build_fact_sheet(facts[type].renewable)
    } else {
        document.getElementById(`${type}-renewable-data`).innerHTML = 'Error'
        document.getElementById(`${type}-non-renewable-data`).innerHTML = 'Error'
    }
}

const numberFormatter = new Intl.NumberFormat('en-US', {
    style: 'decimal',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
});

// Build the list elements which display the consumption and production values for the state
const  build_fact_sheet = (data) => {
    if (data === null) {
        return 'Error';
    }
    let html = '<ul>';
    for (const key in data) {
        if (data.hasOwnProperty(key)) {
            const value = data[key];
            if (typeof value === 'number') {
                html += `<li>${title_case(key)}: ${numberFormatter.format(value)}</li>`;
            } else if (typeof value === 'string') {
                html += `<li>${title_case(key)}: ${value}</li>`;
            }
        }
    }
    html += '</ul>';
    return html;
};

const title_case = string =>{
    return string.toLowerCase()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Handles the updating of the page when a state is clicked, presenting the fact data and getting the model summary
// and recommendations for the state.
const update_state_section = async (state_name, state_abbr, json_data) => {
    const header_element = document.getElementById("text-header");
    header_element.innerHTML = `${state_name} (${state_abbr})`;
    header_element.setAttribute('aria-busy', true);

    const data  = json_data[state_abbr];
    update_state_facts(data, 'consumption')
    update_state_facts(data, 'production')
    const payload = {
        state: state_abbr,
        data
    };

    update_state_summaries(payload, 'summary');
    update_state_summaries(payload, 'recommendation');

    header_element.setAttribute('aria-busy', false);
}

// On page load, builds a mapping of each state to its production and consumption data
const build_fact_map = arr => {
    const is_unknown = data => data === null || data === undefined ? 'Unknown' : data;
    const result = {};
    arr.forEach(data => {
        const consumption = {
            total: is_unknown(data.total_consumption),
            percent_renewable: is_unknown(data.percent_renewable_consumption),
            percent_non_renewable: is_unknown(data.percent_non_renewable_consumption),
            non_renewable: {
                coal: is_unknown(data.coal_consumption),
                gas: is_unknown(data.gas_consumption),
                oil: is_unknown(data.oil_consumption),
                nuclear: is_unknown(data.nuclear_consumption)
            },
            renewable: {
                biomass: is_unknown(data.biomass_consumption),
                geothermal: is_unknown(data.geothermal_consumption),
                hydroelectric: is_unknown(data.hydroelectric_consumption),
                solar: is_unknown(data.solar_consumption),
                wind: is_unknown(data.wind_consumption)
            }
        };

        const production = {
            total: is_unknown(data.total_production),
            percent_renewable: is_unknown(data.percent_renewable_production),
            percent_non_renewable: is_unknown(data.percent_non_renewable_production),
            non_renewable: {
                coal: is_unknown(data.coal_production),
                gas: is_unknown(data.gas_production),
                oil: is_unknown(data.oil_production),
                nuclear: is_unknown(data.nuclear_production)
            },
            renewable: {
                biomass: is_unknown(data.biomass_production),
                other: is_unknown(data.other_production),
                fuel: is_unknown(data.fuel_consumption)
            }
        };
        result[data.state] = {
            state_full: is_unknown(data.state_full),
            fips: is_unknown(data.fips),
            net_production_consumption: is_unknown(data.production_consumption_net),
            consumption,
            production
        };
    });

    return result;
};

const draw_map = (column, colors) => {
    return d3.choropleth()
        .geofile('https://d3-geomap.github.io/d3-geomap/topojson/countries/USA.json')
        .projection(d3.geoAlbersUsa)
        .colors(colors)
        .duration(1000)
        .column(column)
        .unitId('fips')
        .legend(true);
}

const load_data = (map) => {
    d3.csv('https://state-energy-information.jonathan-keys.com/energy-by-state-and-type.csv')
        .then(data => {
            let json_data = build_fact_map(data);
            map.draw(d3.select('#map').datum(data));
            current_state = 'United States';
            let state_name = 'United States';
            let state_abbr = 'US';
            update_state_section(state_name, state_abbr, json_data);

            const svg = d3.select("#map").select("svg");
            svg.on("click", async function (event) {
                if (event.target.tagName === "path") {
                    const properties = event.target.__data__.properties;
                    const fips_id = properties.fips;
                    state_name = properties.name;
                    state_abbr = fips_to_state_abbr[fips_id];

                    if (current_state === state_name) {
                        current_state = 'United States';
                        state_name = 'United States';
                        state_abbr = 'US';
                    } else {
                        current_state = state_name;
                    }
                    await update_state_section(state_name, state_abbr, json_data);

                } else {
                    if (current_state !== 'United States') {
                        current_state = 'United States';
                        state_name = 'United States';
                        state_abbr = 'US';
                        await update_state_section(state_name, state_abbr, json_data);
                    }
                }
            });
        });
}


// Loads initial map of page load
let map = draw_map('percent_renewable_consumption', d3.schemeGreens[9]);
load_data(map);

// Handles changing of the map to a different visualization
const dropdown = document.getElementById('map-choice');
document.querySelectorAll('#map-choice li').forEach((item) => {
    item.addEventListener('click', (event) => {
        const selectedValue = item.getAttribute('data-value');
        document.getElementById('map-title').textContent = item.textContent;
        const color = selectedValue.includes('non_renewable') ? d3.schemeBlues[9] : d3.schemeGreens[9];
        document.getElementById('map').innerHTML = '';
        map =  draw_map(selectedValue, color);
        load_data(map);
        dropdown.removeAttribute('open'); // This collapses the dropdown
    });
});
