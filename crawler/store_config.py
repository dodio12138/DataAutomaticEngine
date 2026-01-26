# 店铺名称与对应的ID
store_dict_panda = {
    "海底捞火锅（Piccadilly）": "18728",
    "海底捞冒菜（Piccadilly）": "18846",
    # "海底捞面馆（Piccadilly）": "334122748",
    # "海底捞面馆（东伦敦）": "261542428",
    "海底捞冒菜（东伦敦）": "682512529",
    "海底捞冒菜（巴特西）": "689260161",
    "海底捞冒菜（Brent）": "843479068",
    "海底捞冒菜（塔桥）": "622889629",
    "海底捞火锅（Piccadilly）东区专送": "318426504",
    "海底捞火锅（Tower Bridge）": "728556608",
    # "海底捞冒菜（Wood Green）": "750724472"
}

store_login_user = {
    "海底捞火锅（Piccadilly）": "8888888888",
    "海底捞冒菜（Piccadilly）": "8888888888",
    "海底捞冒菜（东伦敦）": "8888888888",
    "海底捞冒菜（巴特西）": "8888888888",
    "海底捞冒菜（Brent）": "8888888888",
    "海底捞冒菜（塔桥）": "7346357000",
    "海底捞火锅（Piccadilly）东区专送": "8888888888",
    "海底捞火锅（Tower Bridge）": "7346357000",
}

store_login_password = {
    "海底捞火锅（Piccadilly）": "q26PU5Qr0",
    "海底捞冒菜（Piccadilly）": "q26PU5Qr0",
    "海底捞冒菜（东伦敦）": "q26PU5Qr0",
    "海底捞冒菜（巴特西）": "q26PU5Qr0",
    "海底捞冒菜（Brent）": "q26PU5Qr0",
    "海底捞冒菜（塔桥）": "hdl12345",
    "海底捞火锅（Piccadilly）东区专送": "q26PU5Qr0",
    "海底捞火锅（Tower Bridge）": "hdl12345",
}

store_dict_deliveroo = {
    "海底捞火锅（Piccadilly）": "526324-228737",
    "海底捞冒菜（Piccadilly）": "526324-232978",
    # "海底捞面馆（Piccadilly）": "526324-660307",
    # "海底捞面馆（塔桥店）": "526324-688826",
    "海底捞冒菜（塔桥）": "526324-688829",
    # "海底捞面馆（北伦敦）": "526324-688828",
    # "海底捞冒菜（北伦敦）": "526324-688825",
    # "海底捞面馆（东伦敦）": "526324-694264",
    "海底捞冒菜（东伦敦）": "526324-694265",
    "海底捞冒菜（巴特西）": "526324-717304",
    "海底捞冒菜（Brent）": "526324-717307",
}

# 英文店铺代码（API/环境变量传参使用）→ 中文店铺名
# 仅作为 API 选择与爬虫入参之用，便于避免中文兼容性问题
store_code_map = {
    "piccadilly_hotpot": "海底捞火锅（Piccadilly）",
    "piccadilly_maocai": "海底捞冒菜（Piccadilly）",
    "east_maocai": "海底捞冒菜（东伦敦）",
    "battersea_maocai": "海底捞冒菜（巴特西）",
    "brent_maocai": "海底捞冒菜（Brent）",
    "towerbridge_maocai": "海底捞冒菜（塔桥）",
    "piccadilly_hotpot_east": "海底捞火锅（Piccadilly）东区专送",
    "towerbridge_hotpot": "海底捞火锅（Tower Bridge）",
}

# 反向映射：中文名 → 英文代码
store_name_to_code = {v: k for k, v in store_code_map.items()}
