function parseViewBox(raw) {
  const [x, y, width, height] = String(raw || "-450 -330 900 660")
    .trim()
    .split(/\s+/)
    .map(Number);
  return { x, y, width, height };
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function isFiniteNumber(value) {
  return Number.isFinite(Number(value));
}

const defaultViewBox = parseViewBox(document.getElementById("graphSvg").getAttribute("viewBox"));
const TEXT = {
  cn: {
    sceneLabel: "场景",
    nodeInfoTitle: "节点信息",
    metricsTitle: "Score",
    metricsEmpty: "当前场景没有评分数据。",
    worldMetricsTitle: "World",
    worldSystemTitle: "System",
    roleMetricsTitle: "Resident / NPC",
    residentNeedsTitle: "需求",
    topIssuesTitle: "主要问题",
    worldScore: "世界分",
    humanScore: "人类分",
    entropyScore: "熵稳定度",
    collapsePressure: "崩塌压力",
    entropy: "世界熵",
    collapseStage: "世界阶段",
    weather: "天气",
    seasonName: "季节",
    weekdayName: "星期",
    cleanlinessScore: "清洁度",
    orderlinessScore: "整洁度",
    safetyScore: "安全分",
    roleScore: "总分",
    moodScore: "心情分",
    efficiencyScore: "效率分",
    healthScore: "健康度",
    comfortScore: "舒适度",
    physiologicalNeedScore: "生理需求",
    safetyNeedScore: "安全需求",
    socialNeedScore: "社交需求",
    esteemNeedScore: "尊重需求",
    selfActualizationScore: "自我实现",
    floorListTitle: "楼层",
    legendTitle: "图例",
    legendNodesTitle: "节点",
    legendSemanticTitle: "对象语义",
    legendEdgesTitle: "连线",
    legendRoomLabel: "房间",
    legendFixtureLabel: "设施",
    legendMovableLabel: "可移动物体",
    legendAgentLabel: "智能体",
    legendSemanticFurniture: "家具",
    legendSemanticAppliance: "设备",
    legendSemanticControl: "控制",
    legendSemanticContainer: "容器",
    legendSemanticTool: "工具",
    legendSemanticDecoration: "装饰品",
    legendSemanticConsumable: "消耗品",
    legendSemanticPersonalItem: "个人物品",
    legendSemanticAgent: "智能体",
    legendStatesTitle: "状态颜色",
    legendEdgeNeighborLabel: "房间邻接",
    legendEdgeContainsLabel: "包含/位于其中",
    legendEdgeControlsLabel: "控制关系",
    legendStateFresh: "健康/新鲜",
    legendStateWilted: "枯萎/异常",
    legendStateOn: "运行中",
    legendStateOpen: "开启/开门",
    legendStateCold: "冷藏/低温",
    legendStateWarm: "温热",
    legendStateSpoiled: "变质",
    legendStateDirty: "脏乱",
    legendStateFull: "满载/待处理",
    emptyInfo: "点击中间画布里的房间或物体查看详情。",
    nodeUnavailable: "当前时间步或当前视图中不可见，保留上次选中信息。",
    kind: "类型",
    room: "房间",
    floorOnly: "本层节点与边",
    rooms: "个房间",
    robot: "机器人",
    nodes: "个节点",
    edges: "条边",
    agent: "智能体",
    loadingTitle: "加载中...",
    loadingSubtitle: "准备读取场景",
    noScenesTitle: "没有找到可用场景",
    noScenesSubtitle: "请检查 HLR_dataset 下的 scene JSON 资产",
    bootFailTitle: "Graphworld 启动失败",
    timelineTitle: "时间轴",
    timelineSubtitle: "控制场景时间推进",
    runConfigTitle: "运行配置",
    runConfigSubtitle: "在当前场景里发起一次机器人运行",
    timelineStart: "开始",
    timelinePause: "暂停",
    timelineEnd: "结束",
    timelineReset: "归零",
    timelineSpeed: "速率",
    dayLabel: "第 {day} 天",
    timelineCalendarBar: "{weekday} · {season} · {weather} · {stage}",
    stepLabel: "Step {step} / {max}",
    currentActionTitle: "当前动作",
    currentActionEmpty: "当前没有可显示的 agent 动作。",
    currentActionReasoning: "Reasoning",
    currentActionAction: "Action",
    currentActionStatus: "Status",
    replayAnalysisButton: "分析",
    replayAnalysisTitle: "回放分析",
    replayAnalysisEmpty: "当前场景还没有足够的回放数据可供对比。",
    replayAnalysisChartTitle: "多回放世界分曲线",
    replayAnalysisPickerTitle: "对比结果",
    replayAnalysisPickerHint: "勾选想加入对比的回放结果。",
    replayAnalysisAddLabel: "加入对比",
    replayStepTitle: "当前动作",
    replayStepEmpty: "选择一条回放后，这里会显示当前动作和 reasoning。",
    replayConsoleTitle: "回放控制台",
    replayRunSceneLabel: "场景",
    replayRunExperimentLabel: "实验组",
    replayRunModelLabel: "模型",
    replayRunDaysLabel: "天数",
    replayRunTimeoutLabel: "超时",
    replayRunAgentLabel: "Agent ID",
    replayRunButton: "开始一次机器人运行",
    experimentNoRobot: "No Robot",
    experimentFullAgent: "Full Agent",
    experimentPureHuman: "Pure Human",
    runConfigExpand: "展开",
    runConfigCollapse: "收起",
    humanControlTitle: "Human Control",
    humanEndButton: "结束",
    humanActionHint: "将鼠标移动到动作上查看效果。",
    humanNoSession: "当前没有进行中的人类实验。",
    humanNoCandidates: "当前动作类型没有可用目标。",
    humanValidationPrefix: "动作不合法：",
    replayPlay: "播放",
    replayPause: "暂停",
    replayNoSelection: "未选择回放",
    replayLoading: "正在加载回放...",
    replayRunning: "正在启动机器人运行，请稍候...",
    replayEmptyList: "当前还没有回放记录。",
    replayStatusReady: "已连接回放接口，可以选择历史运行或发起新的运行。",
    replayListLoadFail: "回放列表加载失败",
    replayReasoning: "Reasoning",
    replayAction: "Action",
    replayWorldScore: "World Score",
    replayActionIndexLegendTitle: "动作编号映射",
    replayActionIndexLegendText: "0=move, 1=pick, 2=place, 3=press, 4=scan, 5=open, 6=close, 7=brush",
    replaySceneMetrics: "Scene Metrics",
    replayEventLog: "Event Log",
    replayFailedPreconds: "Failed Preconditions",
    replayStepOk: "执行结果",
    replayStatusBar: "Step {step} / {max} · Day {day} · {clock} · World {score}",
    replayTerminated: "已终止",
    replayNotTerminated: "未终止",
    metricTrendTitle: "分数趋势",
    metricWorldTrendTitle: "世界走势",
    metricResidentTrendTitle: "Resident 走势",
    modeScene: "运行模式",
    modeReplay: "回放模式",
    langButton: "EN",
    kindLabels: { room: "房间", fixture: "设施", movable: "可移动物体", agent: "智能体" },
  },
  en: {
    sceneLabel: "Scene",
    nodeInfoTitle: "Node Info",
    metricsTitle: "Score",
    metricsEmpty: "No metrics available for this scene.",
    worldMetricsTitle: "World Metrics",
    worldSystemTitle: "System",
    roleMetricsTitle: "Residents",
    residentNeedsTitle: "Needs",
    topIssuesTitle: "Issues",
    worldScore: "World score",
    humanScore: "Human score",
    entropyScore: "Entropy stability",
    collapsePressure: "Collapse pressure",
    entropy: "World entropy",
    collapseStage: "World stage",
    weather: "Weather",
    seasonName: "Season",
    weekdayName: "Weekday",
    cleanlinessScore: "Cleanliness",
    orderlinessScore: "Orderliness",
    safetyScore: "Safety",
    roleScore: "Score",
    moodScore: "Mood",
    efficiencyScore: "Efficiency",
    healthScore: "Health",
    comfortScore: "Comfort",
    physiologicalNeedScore: "Physiological",
    safetyNeedScore: "Safety need",
    socialNeedScore: "Social",
    esteemNeedScore: "Esteem",
    selfActualizationScore: "Self-actualization",
    floorListTitle: "Floors",
    legendTitle: "Legend",
    legendNodesTitle: "Nodes",
    legendSemanticTitle: "Object Semantics",
    legendEdgesTitle: "Edges",
    legendRoomLabel: "Room",
    legendFixtureLabel: "Fixture",
    legendMovableLabel: "Movable",
    legendAgentLabel: "Agent",
    legendSemanticFurniture: "Furniture",
    legendSemanticAppliance: "Appliance",
    legendSemanticControl: "Control",
    legendSemanticContainer: "Container",
    legendSemanticTool: "Tool",
    legendSemanticDecoration: "Decoration",
    legendSemanticConsumable: "Consumable",
    legendSemanticPersonalItem: "Personal Item",
    legendSemanticAgent: "Agent",
    legendStatesTitle: "State Colors",
    legendEdgeNeighborLabel: "Room adjacency",
    legendEdgeContainsLabel: "Contains / inside",
    legendEdgeControlsLabel: "Control relation",
    legendStateFresh: "Fresh / healthy",
    legendStateWilted: "Wilted / warning",
    legendStateOn: "Active",
    legendStateOpen: "Open",
    legendStateCold: "Cold",
    legendStateWarm: "Warm",
    legendStateSpoiled: "Spoiled",
    legendStateDirty: "Dirty / messy",
    legendStateFull: "Full / pending",
    emptyInfo: "Click a room or object in the canvas to inspect details.",
    nodeUnavailable: "Not visible in the current step or view. Keeping the last selected info.",
    kind: "Type",
    room: "Room",
    floorOnly: "Nodes and edges on this floor",
    rooms: "rooms",
    robot: "Robot",
    nodes: "nodes",
    edges: "edges",
    agent: "Agent",
    loadingTitle: "Loading...",
    loadingSubtitle: "Preparing scene data",
    noScenesTitle: "No scenes found",
    noScenesSubtitle: "Check the scene JSON assets under HLR_dataset",
    bootFailTitle: "Graphworld failed to start",
    timelineTitle: "Timeline",
    timelineSubtitle: "Control scene time progression",
    runConfigTitle: "Run Config",
    runConfigSubtitle: "Launch a robot run in the current scene",
    timelineStart: "Start",
    timelinePause: "Pause",
    timelineEnd: "End",
    timelineReset: "Reset",
    timelineSpeed: "Speed",
    dayLabel: "Day {day}",
    timelineCalendarBar: "{weekday} · {season} · {weather} · {stage}",
    stepLabel: "Step {step} / {max}",
    currentActionTitle: "Current Action",
    currentActionEmpty: "No agent action is available right now.",
    currentActionReasoning: "Reasoning",
    currentActionAction: "Action",
    currentActionStatus: "Status",
    replayAnalysisButton: "Analysis",
    replayAnalysisTitle: "Replay Analysis",
    replayAnalysisEmpty: "Not enough replay data is available for comparison.",
    replayAnalysisChartTitle: "World Score Comparison",
    replayAnalysisPickerTitle: "Comparison Set",
    replayAnalysisPickerHint: "Select the replay results to compare.",
    replayAnalysisAddLabel: "Add to comparison",
    replayStepTitle: "Current Action",
    replayStepEmpty: "Select a replay to inspect the current action and reasoning.",
    replayConsoleTitle: "Replay Console",
    replayRunSceneLabel: "Scene",
    replayRunExperimentLabel: "Experiment",
    replayRunModelLabel: "Model",
    replayRunDaysLabel: "Days",
    replayRunTimeoutLabel: "Timeout",
    replayRunAgentLabel: "Agent ID",
    replayRunButton: "Start Robot Run",
    experimentNoRobot: "No Robot",
    experimentFullAgent: "Full Agent",
    experimentPureHuman: "Pure Human",
    runConfigExpand: "Expand",
    runConfigCollapse: "Collapse",
    humanControlTitle: "Human Control",
    humanEndButton: "End",
    humanActionHint: "Hover on an action to preview its effect.",
    humanNoSession: "No active human session.",
    humanNoCandidates: "No legal targets for this action type.",
    humanValidationPrefix: "Illegal action: ",
    replayPlay: "Play",
    replayPause: "Pause",
    replayNoSelection: "No replay selected",
    replayLoading: "Loading replay...",
    replayRunning: "Starting robot run...",
    replayEmptyList: "No replay records yet.",
    replayStatusReady: "Replay APIs are ready. Select a previous run or launch a new one.",
    replayListLoadFail: "Failed to load replay list",
    replayReasoning: "Reasoning",
    replayAction: "Action",
    replayWorldScore: "World Score",
    replayActionIndexLegendTitle: "Action Index Map",
    replayActionIndexLegendText: "0=move, 1=pick, 2=place, 3=press, 4=scan, 5=open, 6=close, 7=brush",
    replaySceneMetrics: "Scene Metrics",
    replayEventLog: "Event Log",
    replayFailedPreconds: "Failed Preconditions",
    replayStepOk: "Execution",
    replayStatusBar: "Step {step} / {max} · Day {day} · {clock} · World {score}",
    replayTerminated: "Terminated",
    replayNotTerminated: "Active",
    metricTrendTitle: "Score Trends",
    metricWorldTrendTitle: "World Trend",
    metricResidentTrendTitle: "Resident Trend",
    modeScene: "Run Mode",
    modeReplay: "Replay Mode",
    langButton: "中文",
    kindLabels: { room: "room", fixture: "fixture", movable: "movable", agent: "agent" },
  },
};

const SCENE_NAME_CN = {
  hospital: "医院场景",
  hotel: "酒店场景",
  library: "图书馆场景",
  office: "办公场景",
  supermarket: "超市场景",
  teaching_building: "教学楼场景",
};

const EXPERIMENT_ORDER = ["no_robot", "full_agent", "pure_human"];

const ROOM_NAME_CN = {
  hall: "电梯厅",
  corridor: "走廊",
  corridor_main: "主走廊",
  corridor_front: "前段走廊",
  corridor_back: "后段走廊",
  corridor_mid: "中段走廊",
  corridor_segment: "走廊分段",
  entrance_lobby: "入口大厅",
  information_triage_desk: "信息分诊台",
  registration: "挂号区",
  payment_billing: "收费结算区",
  emergency: "急诊区",
  outpatient_clinic: "门诊诊室",
  pharmacy: "药房",
  phlebotomy_station: "采血站",
  laboratory: "实验室",
  imaging_radiology: "影像放射科",
  imaging_radiology_support: "影像辅助区",
  endoscopy_center: "内镜中心",
  operating_room: "手术室",
  icu: "重症监护室",
  interventional_center: "介入中心",
  post_anesthesia_care_unit: "麻醉恢复室",
  maternity_obgyn: "妇产科",
  pediatrics: "儿科",
  nurse_station: "护士站",
  family_lounge: "家属等候区",
  clean_utility: "清洁处置间",
  soiled_utility: "污物处理间",
  general_ward: "普通病房",
  ward_toilet: "病房卫生间",
  isolation_ward: "隔离病房",
  isolation_anteroom: "隔离前室",
  administration_office: "行政办公室",
  specialist_clinic: "专科门诊",
  sterile_supply_support: "消毒供应支持区",
  treatment_room: "治疗室",
  back_of_house_support: "后勤支持区",
  ballroom: "宴会厅",
  banquet_kitchen_support: "宴会厨房支持区",
  business_center: "商务中心",
  elevator_lobby: "电梯厅",
  executive_lounge: "行政酒廊",
  fitness_center: "健身中心",
  guestroom_cluster: "客房组团",
  housekeeping_linen: "布草间",
  lobby_lounge_bar: "大堂吧",
  luggage_storage: "行李寄存间",
  meeting_rooms: "会议室组团",
  pool_spa: "泳池水疗区",
  prefunction_foyer: "宴会前厅",
  presidential_suite: "总统套房",
  reception_concierge: "前台礼宾区",
  restrooms: "卫生间",
  rooftop_bar: "屋顶酒吧",
  service_support: "服务支持区",
  signature_restaurant: "特色餐厅",
  sky_terrace: "空中露台",
  staff_service: "员工服务间",
  suite_cluster: "套房组团",
  book_storage_stacks: "书库存储区",
  cafe_corner: "咖啡角",
  discussion_room: "讨论室",
  makerspace: "创客空间",
  multimedia_lab: "多媒体实验室",
  new_arrivals_display: "新书展示区",
  quiet_reading_room: "安静阅读室",
  quiet_study_terrace: "安静学习露台",
  reading_area: "阅读区",
  service_desk: "服务台",
  sorting_receiving: "分拣接收区",
  special_collections_gallery: "特藏展区",
  stacks: "书架区",
  staff_meeting_room: "员工会议室",
  staff_office: "员工办公室",
  boardroom: "董事会议室",
  client_lounge: "客户休息区",
  electrical_switchgear_room: "配电室",
  executive_suite: "行政套间",
  fitness_room: "健身房",
  flex_workspace: "灵活办公区",
  it_idf: "弱电间 IDF",
  it_mdf: "主配线间 MDF",
  mailroom_package: "邮件包裹室",
  maintenance_workshop: "维修车间",
  mechanical_plant_room: "机房设备间",
  meeting_suite: "会议套间",
  open_office: "开放办公区",
  pantry_print: "茶水打印间",
  property_management_office: "物业管理办公室",
  retail_cafe: "零售咖啡角",
  security_reception: "安保前台",
  shared_conference_center: "共享会议中心",
  staff_cafeteria: "员工餐厅",
  telecom_headend: "电信机房",
  training_room: "培训室",
  bakery_kitchen_room: "烘焙后厨",
  cafe_takeaway: "外带咖啡区",
  checkout_zone: "收银区",
  chilled_goods: "冷藏商品区",
  chiller_room: "冷藏库",
  customer_service_desk: "客服台",
  dry_storage: "常温仓",
  electrical_mechanical_room: "机电设备间",
  entrance_plaza: "入口广场",
  exit_packing_area: "出口打包区",
  express_checkout: "快速结账区",
  freezer_room: "冷冻库",
  fresh_zone: "生鲜区",
  hot_kitchen_room: "热食厨房",
  it_comms_room: "通信机房",
  lost_found: "失物招领处",
  meat_cutting_room: "肉类分割间",
  non_food: "非食品区",
  prepared_food: "熟食预制区",
  produce_prep_room: "果蔬备货间",
  qa_inspection_sorting: "质检分拣区",
  receiving_dock: "收货码头",
  records_archive: "档案室",
  seafood_processing_room: "水产处理间",
  seasonal_promo: "季节促销区",
  security_monitoring: "安保监控室",
  staff_canteen: "员工食堂",
  staff_changing_breakroom: "员工更衣休息室",
  staff_training_room: "员工培训室",
  standard_goods: "标准商品区",
  store_management_office: "门店管理办公室",
  waste_recycling_room: "垃圾回收间",
  admin_services: "行政服务区",
  clinic: "医务室",
  computer_art_music: "计算机/美术/音乐教室",
  counseling: "心理辅导室",
  general_classrooms: "普通教室",
  it_janitor: "弱电保洁间",
  it_janitor_mech: "弱电保洁机电维护间",
  library_selfstudy: "自习阅览区",
  multipurpose_hall: "多功能厅",
  project_room: "项目学习室",
  science_labs: "科学实验室",
  seminar_rooms: "研讨室",
  support_rooms: "支持用房",
  teacher_office: "教师办公室",
};

const PHRASE_CN = {
  "elevator hall": "电梯厅",
  "floor cover": "地垫",
  "rack": "架子",
  "seat": "座椅",
  "canopy": "伞具",
  "counter": "柜台",
  "obstruction": "隔离栏",
  "structure": "标识架",
  "machine": "机器",
  "telephone": "电话",
  "signaling device": "信号装置",
  "fixture": "固定装置",
  "implement": "器具",
  "stool": "高脚凳",
  "chair": "椅子",
  "home appliance": "家电",
  "box": "箱子",
  "wheeled vehicle": "手推车",
  "furniture": "家具",
  "plumbing fixture": "卫浴设备",
  "cleaning implement": "清洁工具",
  "medical_equipment": "医疗设备",
};

const TOKEN_CN = {
  entrance: "入口",
  lobby: "大厅",
  information: "信息",
  triage: "分诊",
  desk: "台",
  registration: "挂号",
  payment: "收费",
  billing: "结算",
  emergency: "急诊",
  outpatient: "门诊",
  clinic: "诊室",
  pharmacy: "药房",
  phlebotomy: "采血",
  station: "站",
  laboratory: "实验室",
  imaging: "影像",
  radiology: "放射",
  support: "支持",
  endoscopy: "内镜",
  operating: "手术",
  room: "室",
  general: "普通",
  ward: "病房",
  nurse: "护士",
  family: "家属",
  lounge: "休息区",
  clean: "清洁",
  soiled: "污物",
  utility: "处理间",
  toilet: "卫生间",
  isolation: "隔离",
  administration: "行政",
  office: "办公室",
  specialist: "专科",
  sterile: "无菌",
  treatment: "治疗",
  back: "后",
  house: "勤",
  ballroom: "宴会厅",
  banquet: "宴会",
  kitchen: "厨房",
  business: "商务",
  corridor: "走廊",
  elevator: "电梯",
  executive: "行政",
  fitness: "健身",
  guestroom: "客房",
  cluster: "组团",
  housekeeping: "保洁",
  linen: "布草",
  bar: "吧台",
  luggage: "行李",
  meeting: "会议",
  pool: "泳池",
  spa: "水疗",
  prefunction: "前厅",
  foyer: "门厅",
  presidential: "总统",
  reception: "前台",
  concierge: "礼宾",
  restroom: "卫生间",
  rooftop: "屋顶",
  service: "服务",
  signature: "特色",
  restaurant: "餐厅",
  sky: "空中",
  terrace: "露台",
  staff: "员工",
  suite: "套房",
  book: "书",
  storage: "存储",
  stacks: "书架区",
  cafe: "咖啡",
  corner: "角",
  discussion: "讨论",
  makerspace: "创客空间",
  multimedia: "多媒体",
  new: "新",
  arrivals: "到馆",
  display: "展示",
  quiet: "安静",
  reading: "阅读",
  study: "学习",
  area: "区",
  sorting: "分拣",
  receiving: "接收",
  special: "特藏",
  collections: "馆藏",
  gallery: "展区",
  client: "客户",
  electrical: "电气",
  switchgear: "配电",
  executive: "行政",
  flex: "灵活",
  workspace: "办公区",
  mailroom: "邮件室",
  package: "包裹",
  maintenance: "维修",
  workshop: "车间",
  mechanical: "机房",
  plant: "设备",
  pantry: "茶水",
  print: "打印",
  property: "物业",
  management: "管理",
  retail: "零售",
  security: "安保",
  shared: "共享",
  conference: "会议",
  center: "中心",
  cafeteria: "餐厅",
  telecom: "电信",
  headend: "机房",
  training: "培训",
  bakery: "烘焙",
  takeaway: "外带",
  checkout: "结账",
  chilled: "冷藏",
  goods: "商品",
  chiller: "冷藏库",
  customer: "客户",
  dry: "常温",
  entrance: "入口",
  plaza: "广场",
  exit: "出口",
  packing: "打包",
  express: "快速",
  freezer: "冷冻",
  fresh: "生鲜",
  hot: "热食",
  comms: "通信",
  lost: "失物",
  found: "招领",
  meat: "肉类",
  cutting: "分割",
  non: "非",
  food: "食品",
  prepared: "预制",
  produce: "果蔬",
  qa: "质检",
  inspection: "检验",
  dock: "码头",
  records: "档案",
  archive: "档案",
  seafood: "水产",
  seasonal: "季节",
  promo: "促销",
  monitoring: "监控",
  canteen: "食堂",
  changing: "更衣",
  breakroom: "休息室",
  standard: "标准",
  store: "门店",
  waste: "垃圾",
  recycling: "回收",
  admin: "行政",
  services: "服务",
  computer: "计算机",
  art: "美术",
  music: "音乐",
  counseling: "心理辅导",
  classrooms: "教室",
  janitor: "保洁",
  selfstudy: "自习",
  multipurpose: "多功能",
  project: "项目",
  science: "科学",
  seminar: "研讨",
  teacher: "教师",
  floor: "楼层",
  hall: "大厅",
  cover: "垫",
  seat: "座椅",
  canopy: "伞具",
  obstruction: "隔离栏",
  structure: "结构件",
  machine: "机器",
  signaling: "信号",
  device: "设备",
  implement: "器具",
  stool: "凳子",
  fixture: "装置",
  home: "家用",
  appliance: "设备",
  wheeled: "轮式",
  vehicle: "载具",
  plumbing: "卫浴",
  cleaning: "清洁",
  coffee: "咖啡",
  table: "桌",
  console: "控制台",
  armchair: "扶手椅",
  monitor: "显示器",
  keyboard: "键盘",
  button: "按钮",
  bed: "床",
  cabinet: "柜",
  shelf: "架",
  door: "门",
  wall: "墙",
  clock: "时钟",
  sink: "洗手池",
  soap: "肥皂",
  tissue: "纸巾",
  towel: "毛巾",
  lamp: "灯",
  screen: "屏幕",
  printer: "打印机",
  bottle: "瓶",
  bag: "袋",
  bar: "吧台",
  cart: "推车",
  refrigerator: "冰箱",
  security: "安防",
  camera: "摄像头",
  umbrella: "雨伞",
  pool: "泳池",
  signboard: "导视牌",
  machine: "机器",
  counter: "柜台",
  public: "公共",
  trash: "垃圾",
  rack: "架",
  fixture: "装置",
  floor: "地面",
  cover: "覆盖物",
  signaling: "信号",
  telephone: "电话",
  computer: "计算机",
  canteen: "食堂",
  room: "房间",
  object: "对象",
  tool: "工具",
};

const META_KEY_CN = {
  contained_objects: "房间内对象数",
  neighbors: "邻居数",
  object_type: "对象类型",
  states: "状态",
  affordance_count: "可供性数量",
  current_location: "当前位置",
  relation: "关系",
  edge_type: "边类型",
  category: "类别",
  property: "属性",
  child: "子节点",
  parent: "父节点",
  interactive_actions: "可交互动作",
  is_open: "开启",
  is_on: "通电",
  isRunnning: "运行中",
  current_location: "当前位置",
};

const state = {
  scenes: [],
  currentScene: null,
  currentFloorId: null,
  layoutViews: {},
  lastRenderedMode: null,
  expandedNodes: new Set(),
  selectedNodeSnapshot: null,
  viewBox: { ...defaultViewBox },
  pan: {
    active: false,
    startX: 0,
    startY: 0,
    origin: { ...defaultViewBox },
    moved: false,
  },
  hover: {
    nodeId: null,
    clientX: 0,
    clientY: 0,
  },
  deviceActivity: {},
  selectedNodeId: null,
  suppressClickUntil: 0,
  lang: localStorage.getItem("graphworld_lang") || "cn",
  uiMode: localStorage.getItem("graphworld_ui_mode") || "scene",
  metricHistoryByScene: {},
  timeline: {
    playing: false,
    timer: null,
    playbackSeq: 0,
    speed: 1,
    currentStep: 0,
    maxStep: 0,
    day: 1,
    startTimeMin: 0,
    minutesPerStep: 10,
    requestSeq: 0,
    pending: false,
  },
  replay: {
    list: [],
    current: null,
    currentId: null,
    stepIndex: 0,
    playing: false,
    timer: null,
    loading: false,
    playSeq: 0,
    sourceSceneId: null,
    metricSeries: [],
    analysisSeries: [],
    analysisCandidates: [],
    analysisSelectedIds: [],
  },
  human: {
    session: null,
    selectedActionType: "move",
    runConfigExpanded: false,
  },
  modelOptions: [],
  graphFlowFitNonce: 0,
  metricsWindow: {
    open: false,
    dragActive: false,
    dragOffsetX: 0,
    dragOffsetY: 0,
    title: "",
    content: "",
  },
};

const SAVED_LAYOUTS_KEY = "graphworld_saved_layouts_v1";

function readSavedLayoutsStore() {
  try {
    const raw = localStorage.getItem(SAVED_LAYOUTS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    console.warn("Failed to read saved graph layouts", error);
    return {};
  }
}

function writeSavedLayoutsStore(store) {
  try {
    localStorage.setItem(SAVED_LAYOUTS_KEY, JSON.stringify(store || {}));
  } catch (error) {
    console.warn("Failed to persist graph layouts", error);
  }
}

function sceneLayoutStorageId(scene) {
  return String(scene?.scene?.id || scene?.id || "");
}

function snapshotViewLayout(view) {
  return {
    layoutSignature: String(view?.__layoutSignature || ""),
    nonAgentLayoutSignature: String(view?.__nonAgentLayoutSignature || ""),
    nodes: Object.fromEntries(
      (view?.nodes || []).filter((node) => !isRoomDoorNode(node)).map((node) => [
        String(node.id),
        {
          x: Number(node.x || 0),
          y: Number(node.y || 0),
          labelX: typeof node.labelX === "number" ? Number(node.labelX) : null,
          labelY: typeof node.labelY === "number" ? Number(node.labelY) : null,
          layout: node.layout ? cloneData(node.layout) : null,
        },
      ])
    ),
  };
}

function applySavedViewLayout(view, savedLayout) {
  if (!view || !savedLayout || typeof savedLayout !== "object") return view;
  if (String(savedLayout.layoutSignature || "") !== String(view.__layoutSignature || "")) return view;
  const savedNodes = savedLayout.nodes || {};
  for (const node of view.nodes || []) {
    if (isRoomDoorNode(node)) continue;
    const savedNode = savedNodes[String(node.id)];
    if (!savedNode) continue;
    if (Number.isFinite(Number(savedNode.x))) node.x = Number(savedNode.x);
    if (Number.isFinite(Number(savedNode.y))) node.y = Number(savedNode.y);
    if (Number.isFinite(Number(savedNode.labelX))) node.labelX = Number(savedNode.labelX);
    if (Number.isFinite(Number(savedNode.labelY))) node.labelY = Number(savedNode.labelY);
    if (savedNode.layout && typeof savedNode.layout === "object") {
      node.layout = cloneData(savedNode.layout);
    }
  }
  placeRoomDoorNodes(view);
  return view;
}

function persistFloorLayout(scene, floorId, view) {
  const sceneId = sceneLayoutStorageId(scene);
  if (!sceneId || !floorId || !view) return;
  const store = readSavedLayoutsStore();
  const sceneLayouts = (store[sceneId] && typeof store[sceneId] === "object") ? store[sceneId] : {};
  sceneLayouts[String(floorId)] = snapshotViewLayout(view);
  store[sceneId] = sceneLayouts;
  writeSavedLayoutsStore(store);
}

const LAYOUT_TUNING = {
  roomLayout: {
    neighborGap: 54,
    neighborSpring: 0.028,
    roomRepulsionPadding: 22,
    roomRepulsionStrength: 0.18,
    globalCenterPull: 0.002,
    damping: 0.86,
    iterations: 140,
  },
  roomClusters: {
    candidateRadiusX: 148,
    candidateRadiusY: 124,
    candidateRings: 4,
    candidateRingScale: 0.34,
    shellInner: 155,
    shellOuter: 225,
    anchorBaseOffset: 44,
    anchorBandStep: 12,
    anchorPull: 0.05019058294732082,
    centerPushFactor: 0.28,
    centerPushStrength: 0.12,
    ownRoomNodePadding: 8,
    otherRoomNodePadding: 21,
    roomNodeRepulsionStrength: 0.7862679844374635,
    roomRepulsionPadding: 28,
    roomRepulsionStrength: 0.18233988979929985,
    controlEdgeAttraction: 0.052,
    controlCorridorPadding: 24,
    controlCorridorRepulsionStrength: 0.22,
    corridorPadding: 26,
    corridorRepulsionStrength: 0.34600030941905546,
    clusterRepulsionPadding: 16,
    clusterRepulsionStrength: 0.1704882139623179,
    damping: 0.82,
    iterations: 193,
  },
  childGrid: {
    gapX: 40,
    gapY: 33,
  },
  labels: {
    hidePenalty: 1010,
  },
  viewFit: {
    targetWidth: 760,
    targetHeight: 560,
  },
};

const elkInstance = typeof ELK !== "undefined" ? new ELK() : null;
const sceneSelect = document.getElementById("sceneSelect");
const sceneTitle = document.getElementById("sceneTitle");
const floorTitle = document.getElementById("floorTitle");
const sceneStats = document.getElementById("sceneStats");
const floorList = document.getElementById("floorList");
const nodeInfo = document.getElementById("nodeInfo");
const graphFlowContainer = document.getElementById("graphFlow");
const metricsPanel = document.getElementById("metricsPanel");
const graphSvg = document.getElementById("graphSvg");
const hoverTooltip = document.getElementById("hoverTooltip");
const scenePickerLabel = document.getElementById("scenePickerLabel");
const nodeInfoTitle = document.getElementById("nodeInfoTitle");
const metricsTitle = document.getElementById("metricsTitle");
const floorListTitle = document.getElementById("floorListTitle");
const legendTitle = document.getElementById("legendTitle");
const legendNodesTitle = document.getElementById("legendNodesTitle");
const legendSemanticTitle = document.getElementById("legendSemanticTitle");
const legendEdgesTitle = document.getElementById("legendEdgesTitle");
const legendRoomLabel = document.getElementById("legendRoomLabel");
const legendFixtureLabel = document.getElementById("legendFixtureLabel");
const legendMovableLabel = document.getElementById("legendMovableLabel");
const legendAgentLabel = document.getElementById("legendAgentLabel");
const legendSemanticFurniture = document.getElementById("legendSemanticFurniture");
const legendSemanticAppliance = document.getElementById("legendSemanticAppliance");
const legendSemanticControl = document.getElementById("legendSemanticControl");
const legendSemanticContainer = document.getElementById("legendSemanticContainer");
const legendSemanticTool = document.getElementById("legendSemanticTool");
const legendSemanticDecoration = document.getElementById("legendSemanticDecoration");
const legendSemanticConsumable = document.getElementById("legendSemanticConsumable");
const legendSemanticPersonalItem = document.getElementById("legendSemanticPersonalItem");
const legendSemanticAgent = document.getElementById("legendSemanticAgent");
const legendStatesTitle = document.getElementById("legendStatesTitle");
const legendEdgeNeighborLabel = document.getElementById("legendEdgeNeighborLabel");
const legendEdgeContainsLabel = document.getElementById("legendEdgeContainsLabel");
const legendEdgeControlsLabel = document.getElementById("legendEdgeControlsLabel");
const legendStateFresh = document.getElementById("legendStateFresh");
const legendStateWilted = document.getElementById("legendStateWilted");
const legendStateOn = document.getElementById("legendStateOn");
const legendStateOpen = document.getElementById("legendStateOpen");
const legendStateCold = document.getElementById("legendStateCold");
const legendStateWarm = document.getElementById("legendStateWarm");
const legendStateSpoiled = document.getElementById("legendStateSpoiled");
const legendStateDirty = document.getElementById("legendStateDirty");
const legendStateFull = document.getElementById("legendStateFull");
const langToggle = document.getElementById("langToggle");
const timelineTitle = document.getElementById("timelineTitle");
const timelineSubtitle = document.getElementById("timelineSubtitle");
const timelineClock = document.getElementById("timelineClock");
const timelineStep = document.getElementById("timelineStep");
const timelineStart = document.getElementById("timelineStart");
const timelinePause = document.getElementById("timelinePause");
const timelineEnd = document.getElementById("timelineEnd");
const timelineReset = document.getElementById("timelineReset");
const runConfigTitle = document.getElementById("runConfigTitle");
const runConfigSubtitle = document.getElementById("runConfigSubtitle");
const runConfigToggle = document.getElementById("runConfigToggle");
const timelineRunConfig = document.getElementById("timelineRunConfig");
const replayStepTitle = document.getElementById("replayStepTitle");
const replayStepPanel = document.getElementById("replayStepPanel");
const replayConsoleTitle = document.getElementById("replayConsoleTitle");
const replayRunScene = document.getElementById("replayRunScene");
const replayRunExperiment = document.getElementById("replayRunExperiment");
const replayRunModel = document.getElementById("replayRunModel");
const replayRunDays = document.getElementById("replayRunDays");
const replayRunTimeout = document.getElementById("replayRunTimeout");
const replayRunAgent = document.getElementById("replayRunAgent");
const replayRunButton = document.getElementById("replayRunButton");
const replaySummaryBar = document.getElementById("replaySummaryBar");
const replayList = document.getElementById("replayList");
const replayAnalysisButton = document.getElementById("replayAnalysisButton");
const replaySlider = document.getElementById("replaySlider");
const replayReadout = document.getElementById("replayReadout");
const replayFirst = document.getElementById("replayFirst");
const replayPrev = document.getElementById("replayPrev");
const replayPlay = document.getElementById("replayPlay");
const replayPause = document.getElementById("replayPause");
const replayNext = document.getElementById("replayNext");
const replayLast = document.getElementById("replayLast");
const replayRunSceneLabel = document.getElementById("replayRunSceneLabel");
const replayRunExperimentLabel = document.getElementById("replayRunExperimentLabel");
const replayRunModelLabel = document.getElementById("replayRunModelLabel");
const replayRunDaysLabel = document.getElementById("replayRunDaysLabel");
const replayRunTimeoutLabel = document.getElementById("replayRunTimeoutLabel");
const replayRunAgentLabel = document.getElementById("replayRunAgentLabel");
const modeScene = document.getElementById("modeScene");
const modeReplay = document.getElementById("modeReplay");
const nodeInfoCard = document.getElementById("nodeInfoCard");
const metricsCard = document.getElementById("metricsCard");
const metricsExpandButton = document.getElementById("metricsExpandButton");
const metricsWindow = document.getElementById("metricsWindow");
const metricsWindowHeader = document.getElementById("metricsWindowHeader");
const metricsWindowTitle = document.getElementById("metricsWindowTitle");
const metricsWindowKicker = document.getElementById("metricsWindowKicker");
const metricsWindowClose = document.getElementById("metricsWindowClose");
const metricsWindowBody = document.getElementById("metricsWindowBody");
const replayStepCard = document.getElementById("replayStepCard");
const replayConsoleCard = document.getElementById("replayConsoleCard");
const humanControlCard = document.getElementById("humanControlCard");
const humanControlTitle = document.getElementById("humanControlTitle");
const humanEndButton = document.getElementById("humanEndButton");
const humanSummaryBar = document.getElementById("humanSummaryBar");
const humanActionHint = document.getElementById("humanActionHint");
const humanActionTypes = document.getElementById("humanActionTypes");
const humanActionCandidates = document.getElementById("humanActionCandidates");
const floorCard = document.getElementById("floorCard");
const legendCard = document.getElementById("legendCard");
const timelinePanel = document.getElementById("timelinePanel");
const timelineSpeedButtons = [
  document.getElementById("timelineSpeed1x"),
  document.getElementById("timelineSpeed3x"),
  document.getElementById("timelineSpeed10x"),
  document.getElementById("timelineSpeed100x"),
];

function t() {
  return TEXT[state.lang] || TEXT.cn;
}

function kindLabel(kind) {
  return t().kindLabels[kind] || kind;
}

function nodeTypeOf(node) {
  return String(node?.meta?.node_type || "").toLowerCase();
}

function refreshStaticText() {
  document.documentElement.lang = state.lang === "cn" ? "zh-CN" : "en";
  scenePickerLabel.textContent = t().sceneLabel;
  nodeInfoTitle.textContent = t().nodeInfoTitle;
  metricsTitle.textContent = t().metricsTitle;
  if (metricsWindowTitle) metricsWindowTitle.textContent = state.metricsWindow.title || t().metricsTitle;
  if (metricsWindowKicker) metricsWindowKicker.textContent = state.lang === "cn" ? "分数表格" : "Scores only";
  if (metricsExpandButton) metricsExpandButton.textContent = state.lang === "cn" ? "放大" : "Expand";
  if (replayAnalysisButton) replayAnalysisButton.textContent = t().replayAnalysisButton;
  floorListTitle.textContent = t().floorListTitle;
  legendTitle.textContent = t().legendTitle;
  legendNodesTitle.textContent = t().legendNodesTitle;
  legendSemanticTitle.textContent = t().legendSemanticTitle;
  legendEdgesTitle.textContent = t().legendEdgesTitle;
  legendRoomLabel.textContent = t().legendRoomLabel;
  legendFixtureLabel.textContent = t().legendFixtureLabel;
  legendMovableLabel.textContent = t().legendMovableLabel;
  legendAgentLabel.textContent = t().legendAgentLabel;
  legendSemanticFurniture.textContent = t().legendSemanticFurniture;
  legendSemanticAppliance.textContent = t().legendSemanticAppliance;
  legendSemanticControl.textContent = t().legendSemanticControl;
  legendSemanticContainer.textContent = t().legendSemanticContainer;
  legendSemanticTool.textContent = t().legendSemanticTool;
  legendSemanticDecoration.textContent = t().legendSemanticDecoration;
  legendSemanticConsumable.textContent = t().legendSemanticConsumable;
  legendSemanticPersonalItem.textContent = t().legendSemanticPersonalItem;
  legendSemanticAgent.textContent = t().legendSemanticAgent;
  legendStatesTitle.textContent = t().legendStatesTitle;
  legendEdgeNeighborLabel.textContent = t().legendEdgeNeighborLabel;
  legendEdgeContainsLabel.textContent = t().legendEdgeContainsLabel;
  legendEdgeControlsLabel.textContent = t().legendEdgeControlsLabel;
  legendStateFresh.textContent = t().legendStateFresh;
  legendStateWilted.textContent = t().legendStateWilted;
  legendStateOn.textContent = t().legendStateOn;
  legendStateOpen.textContent = t().legendStateOpen;
  legendStateCold.textContent = t().legendStateCold;
  legendStateWarm.textContent = t().legendStateWarm;
  legendStateSpoiled.textContent = t().legendStateSpoiled;
  legendStateDirty.textContent = t().legendStateDirty;
  legendStateFull.textContent = t().legendStateFull;
  timelineTitle.textContent = t().timelineTitle;
  timelineSubtitle.textContent = t().timelineSubtitle;
  runConfigTitle.textContent = t().runConfigTitle;
  runConfigSubtitle.textContent = t().runConfigSubtitle;
  if (runConfigToggle) runConfigToggle.textContent = state.human.runConfigExpanded ? t().runConfigCollapse : t().runConfigExpand;
  timelineStart.textContent = t().timelineStart;
  timelinePause.textContent = t().timelinePause;
  timelineEnd.textContent = t().timelineEnd;
  timelineReset.textContent = t().timelineReset;
  replayStepTitle.textContent = t().currentActionTitle;
  replayConsoleTitle.textContent = t().replayConsoleTitle;
  replayRunSceneLabel.textContent = t().replayRunSceneLabel;
  replayRunExperimentLabel.textContent = t().replayRunExperimentLabel;
  replayRunModelLabel.textContent = t().replayRunModelLabel;
  replayRunDaysLabel.textContent = t().replayRunDaysLabel;
  replayRunTimeoutLabel.textContent = t().replayRunTimeoutLabel;
  replayRunAgentLabel.textContent = t().replayRunAgentLabel;
  replayRunButton.textContent = t().replayRunButton;
  if (humanControlTitle) humanControlTitle.textContent = t().humanControlTitle;
  if (humanEndButton) humanEndButton.textContent = t().humanEndButton;
  if (humanActionHint) humanActionHint.textContent = t().humanActionHint;
  renderExperimentOptions();
  renderHumanControls();
  replayPlay.textContent = t().replayPlay;
  replayPause.textContent = t().replayPause;
  modeScene.textContent = t().modeScene;
  modeReplay.textContent = t().modeReplay;
  langToggle.textContent = t().langButton;
  if (!state.currentScene) {
    sceneTitle.textContent = t().loadingTitle;
    floorTitle.textContent = t().loadingSubtitle;
  }
  if (!state.replay.current) {
    replayStepPanel.textContent = t().currentActionEmpty;
    replayReadout.textContent = t().replayNoSelection;
  }
}

function applyModeVisibility() {
  const isReplay = state.uiMode === "replay";
  modeScene.classList.toggle("active", !isReplay);
  modeReplay.classList.toggle("active", isReplay);

  nodeInfoCard.classList.add("is-hidden");
  metricsCard.classList.toggle("is-hidden", false);
  replayStepCard.classList.toggle("is-hidden", false);
  replayConsoleCard.classList.toggle("is-hidden", !isReplay);
  humanControlCard.classList.toggle("is-hidden", isReplay || !state.human.session);

  floorCard.classList.toggle("is-hidden", false);
  floorCard.classList.toggle("is-muted", isReplay);
  legendCard.classList.toggle("is-hidden", isReplay);

  timelinePanel.classList.toggle("is-hidden", isReplay);
  if (isReplay) closeMetricsWindow();
}

function setUiMode(mode) {
  state.uiMode = mode === "replay" ? "replay" : "scene";
  localStorage.setItem("graphworld_ui_mode", state.uiMode);
  applyModeVisibility();
}

function renderSceneOptions() {
  sceneSelect.innerHTML = "";
  replayRunScene.innerHTML = "";
  for (const scene of state.scenes) {
    const opt = document.createElement("option");
    opt.value = scene.id;
    opt.textContent = `${scene.name} · ${scene.floor_count}F`;
    sceneSelect.appendChild(opt);
    const replayOpt = document.createElement("option");
    replayOpt.value = scene.id;
    replayOpt.textContent = `${scene.name} · ${scene.floor_count}F`;
    replayRunScene.appendChild(replayOpt);
  }
  if (state.currentScene) {
    sceneSelect.value = state.currentScene.scene.id;
  }
  if (state.replay.sourceSceneId) {
    replayRunScene.value = state.replay.sourceSceneId;
  } else if (state.currentScene?.scene?.id) {
    replayRunScene.value = state.currentScene.scene.id;
  }
}

function experimentLabelByType(type, agentModel = "") {
  const normalized = String(type || "").trim().toLowerCase();
  if (normalized === "no_robot") return t().experimentNoRobot;
  if (normalized === "pure_human") return t().experimentPureHuman;
  return t().experimentFullAgent;
}

function inferExperimentType(item = {}) {
  const explicit = String(item.experiment_type || item.summary?.experiment_type || "").trim().toLowerCase();
  if (EXPERIMENT_ORDER.includes(explicit)) return explicit;
  const agentModel = String(item.agent_model || item.summary?.agent_model || "").trim().toLowerCase();
  if (agentModel === "npc_only_baseline") return "no_robot";
  if (agentModel === "human_player") return "pure_human";
  return "full_agent";
}

function replayExperimentLabel(item = {}) {
  const explicit = String(item.experiment_label || item.summary?.experiment_label || "").trim();
  if (explicit) return explicit;
  return experimentLabelByType(inferExperimentType(item), String(item.agent_model || item.summary?.agent_model || ""));
}

function renderExperimentOptions() {
  if (!replayRunExperiment) return;
  const selected = replayRunExperiment.value || "full_agent";
  replayRunExperiment.innerHTML = "";
  for (const type of EXPERIMENT_ORDER) {
    const opt = document.createElement("option");
    opt.value = type;
    opt.textContent = experimentLabelByType(type);
    replayRunExperiment.appendChild(opt);
  }
  replayRunExperiment.value = EXPERIMENT_ORDER.includes(selected) ? selected : "full_agent";
}

function syncReplayRunPreset() {
  const experimentType = String(replayRunExperiment?.value || "full_agent");
  const options = Array.from(replayRunModel?.options || []).map((opt) => String(opt.value || ""));
  const hasLlm = experimentType === "full_agent";
  if (replayRunModel) replayRunModel.disabled = !hasLlm;
  if (!replayRunModel || !options.length) return;
  const current = String(replayRunModel.value || "");
  const preferStrong = options.find((value) => value.toLowerCase().includes("35b")) || "local-qwen3.5-35b";
  const preferFast = options.find((value) => value.toLowerCase().includes("llama3.1:8b")) || "llama3.1:8b";
  if (experimentType === "full_agent" && (!current || current.toLowerCase().includes("35b"))) {
    replayRunModel.value = options.includes(preferFast) ? preferFast : options[0];
  }
}

function renderModelOptions() {
  if (!replayRunModel) return;
  const selected = replayRunModel.value || "bailian-qwen3.5-flash";
  const options = Array.from(new Set([...(state.modelOptions || []), selected, "bailian-qwen3.5-flash"])).filter(Boolean);
  replayRunModel.innerHTML = "";
  for (const model of options) {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    replayRunModel.appendChild(opt);
  }
  replayRunModel.value = options.includes(selected) ? selected : options[0] || "bailian-qwen3.5-flash";
  syncReplayRunPreset();
}

function applyViewBox() {
  const { x, y, width, height } = state.viewBox;
  graphSvg.setAttribute("viewBox", `${x} ${y} ${width} ${height}`);
}

function formatMetricValue(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return num.toFixed(3);
}

function formatMetricPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  return `${Math.round(clamp(num, 0, 1) * 100)}%`;
}

function humanizeMetricKey(key) {
  return String(key || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());
}

function metricLabel(key) {
  const labels = {
    world_score: t().worldScore,
    human_score: t().humanScore,
    entropy_score: t().entropyScore,
    collapse_pressure: t().collapsePressure,
    entropy: t().entropy,
    collapse_stage: t().collapseStage,
    weather: t().weather,
    season_name: t().seasonName,
    weekday_name: t().weekdayName,
    cleanliness_score: t().cleanlinessScore,
    orderliness_score: t().orderlinessScore,
    safety_score: t().safetyScore,
    role_score: t().roleScore,
    mood_score: t().moodScore,
    efficiency_score: t().efficiencyScore,
    health_score: t().healthScore,
    comfort_score: t().comfortScore,
    physiological_need_score: t().physiologicalNeedScore,
    safety_need_score: t().safetyNeedScore,
    social_need_score: t().socialNeedScore,
    esteem_need_score: t().esteemNeedScore,
  };
  return labels[key] || humanizeMetricKey(key);
}

function recordMetricSnapshot(scene) {
  const sceneId = scene?.scene?.id;
  if (!sceneId) return;
  const step = Number(scene?.timeline?.current_step) || 0;
  const worldMetrics = cloneData(scene?.world_metrics || {}) || {};
  const systemDetails = cloneData((((scene?.scene_metrics || {}).world_details || {}).system) || {}) || {};
  const list = Array.isArray(state.metricHistoryByScene[sceneId]) ? [...state.metricHistoryByScene[sceneId]] : [];
  const nextEntry = { step, world_metrics: worldMetrics, system_details: systemDetails };
  const existingIndex = list.findIndex((item) => Number(item.step) === step);
  if (existingIndex >= 0) {
    list[existingIndex] = nextEntry;
  } else {
    list.push(nextEntry);
  }
  list.sort((left, right) => Number(left.step) - Number(right.step));
  state.metricHistoryByScene[sceneId] = list.slice(-240);
}

function currentMetricHistory() {
  const sceneId = state.currentScene?.scene?.id;
  if (!sceneId) return [];
  return state.metricHistoryByScene[sceneId] || [];
}

function metricChartPath(points, width, height, padding) {
  if (!points.length) return "";
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  return points
    .map((point, index) => {
      const x = padding.left + innerWidth * point.x;
      const y = padding.top + innerHeight * (1 - point.y);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function buildMetricPoints(values) {
  const clean = values.filter((value) => Number.isFinite(Number(value))).map(Number);
  if (!clean.length) return [];
  const maxIndex = Math.max(1, clean.length - 1);
  return clean.map((value, index) => ({
    x: index / maxIndex,
    y: clamp(value, 0, 1),
    value,
  }));
}

function buildTrendContextLabels(labels = [], count = 4) {
  const clean = Array.isArray(labels) ? labels : [];
  if (!clean.length) return [];
  const maxIndex = Math.max(0, clean.length - 1);
  const result = [];
  for (let slot = 0; slot < Math.max(2, count); slot += 1) {
    const rawIndex = Math.round((maxIndex * slot) / Math.max(1, count - 1));
    const index = clamp(rawIndex, 0, maxIndex);
    const item = clean[index];
    if (!item || !item.text) continue;
    if (result.some((existing) => existing.index === index || existing.text === item.text)) continue;
    result.push({
      index,
      text: item.text,
      x: maxIndex === 0 ? 0 : index / maxIndex,
    });
  }
  return result.sort((left, right) => left.x - right.x);
}

function renderTrendChart(title, currentValue, series, options = {}) {
  const width = 320;
  const contextLabels = buildTrendContextLabels(options.contextLabels, options.contextCount || 4);
  const height = contextLabels.length ? 146 : 122;
  const padding = { top: 10, right: 8, bottom: contextLabels.length ? 34 : 12, left: 8 };
  const gridYs = [0.25, 0.5, 0.75].map((tick) => {
    const y = padding.top + (height - padding.top - padding.bottom) * tick;
    return `<line class="metric-chart-grid" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"></line>`;
  }).join("");
  const axisY = height - padding.bottom;
  const seriesSvg = series
    .map((item) => {
      const points = buildMetricPoints(item.values);
      if (!points.length) return "";
      const path = metricChartPath(points, width, height, padding);
      const rawIndex = Number.isFinite(Number(options.highlightIndex)) ? Number(options.highlightIndex) : points.length - 1;
      const highlighted = points[clamp(Math.round(rawIndex), 0, points.length - 1)] || points[points.length - 1];
      const cx = padding.left + (width - padding.left - padding.right) * highlighted.x;
      const cy = padding.top + (height - padding.top - padding.bottom) * (1 - highlighted.y);
      return `
        <path class="metric-chart-line ${item.className}" d="${path}"></path>
        <circle class="metric-chart-point ${item.className}" cx="${cx.toFixed(2)}" cy="${cy.toFixed(2)}" r="4.5"></circle>
      `;
    })
    .join("");
  const legend = series
    .filter((item) => item.values.some((value) => Number.isFinite(Number(value))))
    .map(
      (item) => `
        <span class="metric-chart-legend-item">
          <span class="metric-chart-legend-swatch ${item.className}"></span>
          <span>${item.label}</span>
        </span>
      `
    )
    .join("");
  const contextSvg = contextLabels
    .map((item) => {
      const x = padding.left + (width - padding.left - padding.right) * item.x;
      return `
        <line class="metric-chart-context-tick" x1="${x.toFixed(2)}" y1="${axisY}" x2="${x.toFixed(2)}" y2="${(axisY + 6).toFixed(2)}"></line>
        <text class="metric-chart-context-label" x="${x.toFixed(2)}" y="${(axisY + 18).toFixed(2)}">${escapeHtml(item.text)}</text>
      `;
    })
    .join("");
  return `
    <div class="metric-chart-card">
      <div class="metric-chart-header">
        <div class="metric-chart-title">${title}</div>
        <div class="metric-chart-value">${formatMetricPercent(currentValue)}</div>
      </div>
      <svg class="metric-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
        ${gridYs}
        <line class="metric-chart-axis" x1="${padding.left}" y1="${axisY}" x2="${width - padding.right}" y2="${axisY}"></line>
        ${seriesSvg}
        ${contextSvg}
      </svg>
      ${legend ? `<div class="metric-chart-legend">${legend}</div>` : ""}
    </div>
  `;
}

function renderReplayTrendCards() {
  const series = Array.isArray(state.replay.metricSeries) ? state.replay.metricSeries : [];
  if (!series.length) return "";
  const highlightIndex = clamp(state.replay.stepIndex, 0, Math.max(0, series.length - 1));
  const current = series[highlightIndex] || {};
  const replaySteps = Array.isArray(state.replay.current?.run?.steps) ? state.replay.current.run.steps : [];
  const contextLabels = replaySteps.map((step) => {
    const worldState = (((step || {}).scene || {}).world_state) || {};
    const weekday = String(worldState.weekday_name_cn || worldState.weekday_name || "").trim();
    const season = String(worldState.season_name_cn || worldState.season_name || "").trim();
    return { text: [weekday, season].filter(Boolean).join(" · ") };
  });
  const worldTrend = renderTrendChart(
    t().metricWorldTrendTitle,
    current.world_score,
    [
      { className: "world", label: t().worldScore, values: series.map((item) => item.world_score) },
      { className: "human", label: t().humanScore, values: series.map((item) => item.human_score) },
    ],
    { highlightIndex, contextLabels }
  );
  return worldTrend;
}

function renderReplayMetricsMarkup() {
  const trendMarkup = renderReplayTrendCards();
  const step = replayCurrentStep();
  const scoreMarkup = step
    ? `<div class="metric-group"><div class="metric-section-title">${t().replayWorldScore}</div><div class="metric-grid"><div class="metric-chip"><div class="metric-label">${t().worldScore}</div><div class="metric-value">${formatMetricValue(step.world_score)}</div></div></div></div>`
    : "";
  const actionLegendMarkup = `
    <div class="metric-group">
      <div class="metric-section-title">${t().replayActionIndexLegendTitle}</div>
      <div class="metric-system-line"><span>${escapeHtml(t().replayActionIndexLegendText)}</span></div>
    </div>
  `;
  return `${trendMarkup}${scoreMarkup}${actionLegendMarkup}` || `<div class="metric-empty">${t().metricsEmpty}</div>`;
}

function renderScoreHero(worldMetrics = {}, systemDetails = {}) {
  const cards = [
    { key: "world_score", label: t().worldScore, value: worldMetrics.world_score, hero: true },
    { key: "human_score", label: t().humanScore, value: worldMetrics.human_score, hero: true },
    { key: "cleanliness_score", label: t().cleanlinessScore, value: worldMetrics.cleanliness_score },
    { key: "orderliness_score", label: t().orderlinessScore, value: worldMetrics.orderliness_score },
    { key: "safety_score", label: t().safetyScore, value: worldMetrics.safety_score },
    { key: "entropy_score", label: t().entropyScore, value: worldMetrics.entropy_score },
    { key: "collapse_pressure", label: t().collapsePressure, value: worldMetrics.collapse_pressure },
    { key: "entropy", label: t().entropy, value: systemDetails.entropy },
  ];
  return cards
    .filter((item) => item.value != null)
    .map(
      (item) => `
        <div class="metric-chip ${item.hero ? "metric-chip-hero" : ""}">
          <div class="metric-label">${item.label}</div>
          <div class="metric-value">${formatMetricValue(item.value)}</div>
        </div>
      `
    )
    .join("");
}

function renderSystemLine(systemDetails = {}) {
  const values = [
    systemDetails.weekday_name,
    systemDetails.season_name,
    systemDetails.weather,
    systemDetails.collapse_stage,
  ].filter(Boolean);
  if (!values.length) return "";
  return `<div class="metric-system-line">${values.map((value) => `<span>${escapeHtml(String(value))}</span>`).join("")}</div>`;
}

function renderReplayComparisonChart(seriesList) {
  const valid = Array.isArray(seriesList) ? seriesList.filter((item) => Array.isArray(item.values) && item.values.length) : [];
  if (!valid.length) return `<div class="metric-empty">${t().replayAnalysisEmpty}</div>`;
  const colors = ["#b35c2e", "#4f7f73", "#8a5ea7", "#d17a45", "#2e5fa8", "#7b8f3b"];
  const width = 720;
  const seasonSegments = buildReplaySeasonSegments(valid[0]?.context || []);
  const height = seasonSegments.length ? 274 : 240;
  const padding = { top: 14, right: 12, bottom: seasonSegments.length ? 44 : 18, left: 12 };
  const gridYs = [0.25, 0.5, 0.75].map((tick) => {
    const y = padding.top + (height - padding.top - padding.bottom) * tick;
    return `<line class="metric-chart-grid" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"></line>`;
  }).join("");
  const axisY = height - padding.bottom;
  const lines = valid.map((item, index) => {
    const points = buildMetricPoints(item.values);
    const path = metricChartPath(points, width, height, padding);
    const color = colors[index % colors.length];
    return `<path d="${path}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>`;
  }).join("");
  const seasonSvg = seasonSegments.map((segment, index) => {
    const innerWidth = width - padding.left - padding.right;
    const x1 = padding.left + innerWidth * segment.startX;
    const x2 = padding.left + innerWidth * segment.endX;
    const labelX = (x1 + x2) / 2;
    const divider = index > 0
      ? `<line class="metric-chart-season-divider" x1="${x1.toFixed(2)}" y1="${padding.top}" x2="${x1.toFixed(2)}" y2="${axisY.toFixed(2)}"></line>`
      : "";
    return `
      ${divider}
      <text class="metric-chart-season-label" x="${labelX.toFixed(2)}" y="${(axisY + 20).toFixed(2)}">${escapeHtml(segment.label)}</text>
    `;
  }).join("");
  const legend = valid.map((item, index) => {
    const color = colors[index % colors.length];
    return `<span class="metric-chart-legend-item"><span class="metric-chart-legend-swatch" style="background:${color}"></span><span>${escapeHtml(item.label)}</span></span>`;
  }).join("");
  const summaries = valid.map((item) => `
    <div class="metric-chip">
      <div class="metric-label">${escapeHtml(item.label)}</div>
      <div class="metric-value">${formatMetricValue(item.finalScore)}</div>
    </div>
  `).join("");
  return `
    <div class="metric-group">
      <div class="metric-section-title">${t().replayAnalysisChartTitle}</div>
      <div class="metric-chart-card">
        <svg class="metric-chart-svg metric-chart-svg-wide" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
          ${gridYs}
          <line class="metric-chart-axis" x1="${padding.left}" y1="${axisY}" x2="${width - padding.right}" y2="${axisY}"></line>
          ${lines}
          ${seasonSvg}
        </svg>
        <div class="metric-chart-legend">${legend}</div>
      </div>
      <div class="metric-grid">${summaries}</div>
    </div>
  `;
}

function buildReplaySeasonSegments(context = []) {
  const clean = Array.isArray(context) ? context.map((item) => String(item?.season || "").trim()) : [];
  if (!clean.length) return [];
  const maxIndex = Math.max(1, clean.length - 1);
  const segments = [];
  let start = 0;
  let current = clean[0] || "";
  for (let index = 1; index < clean.length; index += 1) {
    const next = clean[index] || current;
    if (next === current) continue;
    segments.push({
      label: current || next,
      startX: start / maxIndex,
      endX: (index - 1) / maxIndex,
    });
    start = index;
    current = next;
  }
  segments.push({
    label: current || clean[clean.length - 1] || "",
    startX: start / maxIndex,
    endX: 1,
  });
  return segments.filter((segment) => segment.label);
}

function replayAnalysisDefaults(items) {
  const ids = [];
  const currentId = String(state.replay.currentId || "");
  if (currentId) ids.push(currentId);
  for (const item of items || []) {
    const replayId = String(item.replayId || "");
    if (!replayId || ids.includes(replayId)) continue;
    ids.push(replayId);
    if (ids.length >= 4) break;
  }
  return ids;
}

function renderReplayAnalysisPicker(items = [], selectedIds = []) {
  if (!items.length) return "";
  const selected = new Set(selectedIds.map(String));
  const cards = items.map((item) => {
    const checked = selected.has(String(item.replayId));
    return `
      <label class="replay-analysis-option ${checked ? "active" : ""}">
        <input class="replay-analysis-toggle" type="checkbox" value="${escapeHtml(String(item.replayId))}" ${checked ? "checked" : ""} />
        <div class="replay-analysis-option-body">
          <div class="replay-analysis-option-title">${escapeHtml(item.title)}</div>
          <div class="replay-analysis-option-meta">${escapeHtml(item.meta)}</div>
        </div>
      </label>
    `;
  }).join("");
  return `
    <div class="metric-group">
      <div class="metric-section-title">${t().replayAnalysisPickerTitle}</div>
      <div class="metric-empty metric-empty-inline">${t().replayAnalysisPickerHint}</div>
      <div class="replay-analysis-list">${cards}</div>
    </div>
  `;
}

function renderReplayAnalysisMarkup() {
  const selected = new Set((state.replay.analysisSelectedIds || []).map(String));
  const selectedSeries = (state.replay.analysisCandidates || []).filter((item) => selected.has(String(item.replayId)));
  return `
    ${renderReplayAnalysisPicker(state.replay.analysisCandidates, state.replay.analysisSelectedIds)}
    ${renderReplayComparisonChart(selectedSeries)}
  `;
}

function bindReplayAnalysisControls() {
  if (!metricsWindowBody) return;
  const toggles = metricsWindowBody.querySelectorAll(".replay-analysis-toggle");
  for (const toggle of toggles) {
    toggle.addEventListener("change", () => {
      const selectedIds = Array.from(metricsWindowBody.querySelectorAll(".replay-analysis-toggle:checked"))
        .map((input) => String(input.value || ""));
      state.replay.analysisSelectedIds = selectedIds;
      const markup = renderReplayAnalysisMarkup();
      syncMetricsWindowContent(markup, t().replayAnalysisTitle);
      bindReplayAnalysisControls();
    });
  }
}

function renderProgressMetric(label, value) {
  const num = Number(value);
  const normalized = Number.isFinite(num) ? clamp(num, 0, 1) : 0;
  return `
    <div class="metric-progress-item">
      <div class="metric-progress-top">
        <div class="metric-progress-label">${label}</div>
        <div class="metric-progress-value">${formatMetricPercent(value)}</div>
      </div>
      <div class="metric-progress-track">
        <div class="metric-progress-fill" style="width: ${normalized * 100}%"></div>
      </div>
    </div>
  `;
}

function syncMetricsWindowContent(markup, title = state.metricsWindow.title || t().metricsTitle) {
  if (!metricsWindowBody) return;
  state.metricsWindow.content = markup;
  state.metricsWindow.title = title;
  metricsWindowBody.innerHTML = markup;
  if (metricsWindowTitle) metricsWindowTitle.textContent = title;
}

function openMetricsWindow(title = state.metricsWindow.title || t().metricsTitle, markup = state.metricsWindow.content) {
  if (!metricsWindow) return;
  state.metricsWindow.open = true;
  state.metricsWindow.title = title;
  metricsWindow.hidden = false;
  syncMetricsWindowContent(markup || `<div class="metric-empty">${t().metricsEmpty}</div>`, title);
}

function closeMetricsWindow() {
  if (!metricsWindow) return;
  state.metricsWindow.open = false;
  state.metricsWindow.dragActive = false;
  metricsWindow.hidden = true;
}

function beginMetricsWindowDrag(event) {
  if (!metricsWindow || event.button !== 0) return;
  const rect = metricsWindow.getBoundingClientRect();
  state.metricsWindow.dragActive = true;
  state.metricsWindow.dragOffsetX = event.clientX - rect.left;
  state.metricsWindow.dragOffsetY = event.clientY - rect.top;
}

function moveMetricsWindow(event) {
  if (!metricsWindow || !state.metricsWindow.dragActive) return;
  const nextLeft = clamp(event.clientX - state.metricsWindow.dragOffsetX, 8, window.innerWidth - 120);
  const nextTop = clamp(event.clientY - state.metricsWindow.dragOffsetY, 8, window.innerHeight - 120);
  metricsWindow.style.left = `${nextLeft}px`;
  metricsWindow.style.top = `${nextTop}px`;
}

function endMetricsWindowDrag() {
  state.metricsWindow.dragActive = false;
}

function renderMetrics() {
  if (!metricsPanel) return;
  const worldMetrics = state.currentScene?.world_metrics || {};
  const systemDetails = (((state.currentScene?.scene_metrics || {}).world_details || {}).system) || {};
  const history = currentMetricHistory();
  const hasWorld = Object.keys(worldMetrics).length > 0;
  const hasSystem = Object.keys(systemDetails).length > 0;
  if (!hasWorld && !hasSystem) {
    metricsPanel.innerHTML = `<div class="metric-empty">${t().metricsEmpty}</div>`;
    syncMetricsWindowContent(metricsPanel.innerHTML);
    return;
  }

  const worldTrend = renderTrendChart(
    t().metricWorldTrendTitle,
    worldMetrics.world_score,
    [
      { className: "world", label: t().worldScore, values: history.map((item) => item.world_metrics?.world_score) },
      { className: "human", label: t().humanScore, values: history.map((item) => item.world_metrics?.human_score) },
    ]
    ,
    {
      contextLabels: history.map((item) => {
        const system = item.system_details || {};
        const weekday = String(system.weekday_name_cn || system.weekday_name || "").trim();
        const season = String(system.season_name_cn || system.season_name || "").trim();
        return { text: [weekday, season].filter(Boolean).join(" · ") };
      }),
    }
  );
  const scoreCards = renderScoreHero(worldMetrics, systemDetails);
  const systemLine = renderSystemLine(systemDetails);
  const metricsMarkup = `
    ${hasWorld ? `<div class="metric-group">${worldTrend}</div>` : ""}
    ${scoreCards ? `<div class="metric-group"><div class="metric-grid metric-grid-compact">${scoreCards}</div></div>` : ""}
    ${systemLine ? `<div class="metric-group">${systemLine}</div>` : ""}
  `;
  metricsPanel.innerHTML = metricsMarkup;
  syncMetricsWindowContent(metricsMarkup);
}

function cloneData(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function formatDayLabel(day) {
  return t().dayLabel.replace("{day}", String(day));
}

function formatStepLabel(step, max) {
  return t().stepLabel.replace("{step}", String(step)).replace("{max}", String(max));
}

function timelineDay(step) {
  return Math.floor((Number(step) || 0) * state.timeline.minutesPerStep / (24 * 60)) + 1;
}

function formatClock(totalMinutes) {
  const minutesInDay = 24 * 60;
  const normalized = ((Number(totalMinutes) % minutesInDay) + minutesInDay) % minutesInDay;
  const hours = Math.floor(normalized / 60);
  const minutes = normalized % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function stopTimelinePlayback() {
  if (state.timeline.timer) {
    clearTimeout(state.timeline.timer);
    state.timeline.timer = null;
  }
  state.timeline.playing = false;
  state.timeline.playbackSeq = (state.timeline.playbackSeq || 0) + 1;
}

function timelineStateFromScene(scene) {
  const timeline = scene?.timeline || {};
  return {
    playing: false,
    timer: null,
    playbackSeq: 0,
    speed: 1,
    currentStep: Number(timeline.current_step) || 0,
    maxStep: Math.max(0, Number(timeline.max_step) || 0),
    day: Number(timeline.day) || 1,
    weekdayName: String(timeline.weekday_name_cn || timeline.weekday_name || ""),
    seasonName: String(timeline.season_name_cn || timeline.season_name || ""),
    weather: String(timeline.weather || ""),
    collapseStage: String(timeline.collapse_stage || ""),
    entropy: Number(timeline.entropy) || 0,
    startTimeMin: Number(timeline.start_time_min) || 0,
    minutesPerStep: Math.max(1, Number(timeline.minutes_per_step) || 10),
    requestSeq: 0,
    pending: false,
  };
}

function currentTimelineMinutes() {
  return state.timeline.startTimeMin;
}

function renderTimeline() {
  const maxStep = state.timeline.maxStep;
  const currentDay = Number(state.timeline.day) || timelineDay(state.timeline.currentStep);
  const maxDay = timelineDay(maxStep);
  const humanActive = !!state.human.session && !state.human.session.terminated;
  const calendarBar = t().timelineCalendarBar
    .replace("{weekday}", state.timeline.weekdayName || "--")
    .replace("{season}", state.timeline.seasonName || "--")
    .replace("{weather}", state.timeline.weather || "--")
    .replace("{stage}", state.timeline.collapseStage || "--");
  timelineClock.textContent = `${formatDayLabel(currentDay)} · ${formatClock(currentTimelineMinutes())} · ${calendarBar}`;
  timelineStep.textContent = `${formatDayLabel(currentDay)} / ${maxDay} · ${t().entropy}: ${formatMetricValue(state.timeline.entropy)}`;
  timelineStart.disabled = humanActive || state.timeline.playing || state.timeline.currentStep >= maxStep;
  timelinePause.disabled = humanActive || !state.timeline.playing;
  timelineEnd.disabled = humanActive || !state.timeline.playing;
  timelineReset.disabled = humanActive || (state.timeline.currentStep === 0 && !state.timeline.playing);
  for (const button of timelineSpeedButtons) {
    if (!button) continue;
    const speed = Number(button.textContent.replace("x", "")) || 1;
    button.classList.toggle("active", speed === state.timeline.speed);
  }
}

function stopReplayPlayback() {
  if (state.replay.timer) {
    clearTimeout(state.replay.timer);
    state.replay.timer = null;
  }
  state.replay.playing = false;
  state.replay.playSeq = (state.replay.playSeq || 0) + 1;
}

function replayDelayMs() {
  return 700;
}

function replayIdForReplay() {
  return String(state.replay.currentId || state.replay.current?.replay_id || "");
}

function replayCurrentStep() {
  return state.replay.stepCache?.[state.replay.stepIndex] || null;
}

function formatClockFromScene(rawScene) {
  return formatClock(Number(rawScene?.world_state?.time_min) || 0);
}

function floorNameFromId(floorId, lang = state.lang) {
  const raw = String(floorId || "");
  const match = raw.match(/^F(\d+)$/i);
  if (match) {
    return lang === "cn" ? `第 ${match[1]} 层` : `Floor ${match[1]}`;
  }
  return raw || (lang === "cn" ? "默认楼层" : "Default Floor");
}

function replayEdgeKind(rawEdge) {
  const relation = String(rawEdge?.relation || "").toLowerCase();
  const category = String(rawEdge?.category || "").toLowerCase();
  if (category === "control" || relation === "controls") return "controls";
  if (["adjacent_to", "neighbour", "neighbor"].includes(relation)) return "neighbor";
  if (relation === "at") return "agent_at";
  if (["contains", "inside_room", "inside_floor", "in", "on", "part_of", "mounted_on", "held_by", "worn_by"].includes(relation)) return "contains";
  if (["transport", "carried_to"].includes(relation)) return "transport";
  if (relation === "ontop") return "ontop";
  if (relation === "next_to") return "next_to";
  return relation || "other";
}

function replayNodeKind(rawNode) {
  const nodeType = String(rawNode?.node_type || "").toLowerCase();
  const semanticType = String(rawNode?.semantic_type || "").toLowerCase();
  if (nodeType === "room" || semanticType === "room") return "room";
  if (nodeType === "agent" || semanticType === "agent" || semanticType === "human" || semanticType === "robot") return "agent";
  if (nodeType === "movable_object") return "movable";
  return "fixture";
}

function replayNodeLabel(rawNode) {
  if (String(rawNode?.semantic_type || "").toLowerCase() === "robot" || String(rawNode?.id || "") === "robot_01") {
    return state.lang === "cn" ? "机器人" : "Robot";
  }
  return state.lang === "cn"
    ? String(rawNode?.name_cn || rawNode?.name || rawNode?.id || "")
    : String(rawNode?.name || rawNode?.name_cn || rawNode?.id || "");
}

function normalizeRectLayoutForReplay(layout) {
  if (!layout || typeof layout !== "object") return null;
  if (!isFiniteNumber(layout.x) || !isFiniteNumber(layout.y) || !isFiniteNumber(layout.w) || !isFiniteNumber(layout.h)) return null;
  return {
    x: Number(layout.x),
    y: Number(layout.y),
    w: Number(layout.w),
    h: Number(layout.h),
    doorways: Array.isArray(layout.doorways)
      ? layout.doorways
          .filter((doorway) => isFiniteNumber(doorway?.x) && isFiniteNumber(doorway?.y) && isFiniteNumber(doorway?.length))
          .map((doorway) => ({
            to: String(doorway.to || ""),
            orientation: String(doorway.orientation || ""),
            x: Number(doorway.x),
            y: Number(doorway.y),
            length: Number(doorway.length),
            width: isFiniteNumber(doorway.width) ? Number(doorway.width) : 0.8,
          }))
      : [],
  };
}

function runtimeMetaOf(node) {
  return cloneData(node?.meta?.runtime || node?.runtime || {}) || {};
}

function connectedRoomsForNode(node) {
  const runtime = runtimeMetaOf(node);
  const raw = Array.isArray(runtime.connected_rooms) ? runtime.connected_rooms : [];
  const rooms = [];
  for (const roomId of raw) {
    const value = String(roomId || "");
    if (value && !rooms.includes(value)) rooms.push(value);
  }
  return rooms;
}

function isRoomDoorNode(node) {
  return String(node?.meta?.semantic_type || node?.semantic_type || "").toLowerCase() === "door" && connectedRoomsForNode(node).length > 0;
}

function roomIdForReplayNode(rawNode, rawNodeById, containsBySource) {
  const kind = replayNodeKind(rawNode);
  if (kind === "room") return String(rawNode?.id || "");
  const runtime = cloneData(rawNode?.runtime || {}) || {};
  const connectedRooms = Array.isArray(runtime.connected_rooms) ? runtime.connected_rooms.map((roomId) => String(roomId || "")).filter(Boolean) : [];
  if (String(rawNode?.semantic_type || "").toLowerCase() === "door" && connectedRooms.length) {
    return connectedRooms[0];
  }
  const directRoom = String(rawNode?.room_id || rawNode?.current_location || "");
  if (directRoom && replayNodeKind(rawNodeById.get(directRoom)) === "room") return directRoom;
  let currentId = String(rawNode?.parent || "");
  const seen = new Set();
  while (currentId && !seen.has(currentId)) {
    seen.add(currentId);
    const current = rawNodeById.get(currentId);
    if (!current) break;
    if (replayNodeKind(current) === "room") return String(current.id || "");
    currentId = String(current.parent || "");
  }
  for (const [roomId, children] of containsBySource.entries()) {
    if (children.has(String(rawNode?.id || "")) && replayNodeKind(rawNodeById.get(roomId)) === "room") {
      return roomId;
    }
  }
  return "";
}

function floorIdForReplayRoom(rawRoom, rawNodeById) {
  let currentId = String(rawRoom?.parent || "");
  const seen = new Set();
  while (currentId && !seen.has(currentId)) {
    seen.add(currentId);
    const current = rawNodeById.get(currentId);
    if (!current) break;
    if (String(current.semantic_type || "").toLowerCase() === "floor") return String(current.id || "");
    currentId = String(current.parent || "");
  }
  return "";
}

function adaptReplayScene(rawScene, replayPayload, stepIndex, stepPayload) {
  const sceneNodes = Array.isArray(rawScene?.nodes) ? rawScene.nodes : [];
  const sceneEdges = Array.isArray(rawScene?.edges) ? rawScene.edges : [];
  const rawNodeById = new Map(sceneNodes.map((node) => [String(node.id), node]));
  const containsBySource = new Map();
  for (const edge of sceneEdges) {
    const kind = replayEdgeKind(edge);
    if (kind !== "contains") continue;
    const source = String(edge.source_id || "");
    const target = String(edge.target_id || "");
    if (!source || !target) continue;
    if (!containsBySource.has(source)) containsBySource.set(source, new Set());
    containsBySource.get(source).add(target);
  }

  const floorNodes = sceneNodes.filter((node) => String(node.semantic_type || "").toLowerCase() === "floor");
  const roomNodes = sceneNodes.filter((node) => replayNodeKind(node) === "room");
  const floorIds = new Set(floorNodes.map((node) => String(node.id)));
  const roomFloorMap = new Map();
  for (const room of roomNodes) {
    const floorId = floorIdForReplayRoom(room, rawNodeById) || "F1";
    roomFloorMap.set(String(room.id), floorId);
    floorIds.add(floorId);
  }
  if (!floorIds.size) floorIds.add("F1");

  const floors = Array.from(floorIds).map((floorId) => {
    const floorNode = rawNodeById.get(floorId);
    const roomCount = roomNodes.filter((node) => roomFloorMap.get(String(node.id)) === floorId).length;
    return {
      id: floorId,
      name: state.lang === "cn"
        ? String(floorNode?.name_cn || floorNode?.name || floorNameFromId(floorId, "cn"))
        : String(floorNode?.name || floorNode?.name_cn || floorNameFromId(floorId, "en")),
      floor_number: Number(floorNode?.floor_number) || Number(String(floorId).replace(/[^\d]/g, "")) || 1,
      room_count: roomCount,
    };
  }).sort((left, right) => left.floor_number - right.floor_number);

  const visibleNodeObjects = [];
  for (const rawNode of sceneNodes) {
    const id = String(rawNode?.id || "");
    if (!id) continue;
    const kind = replayNodeKind(rawNode);
    if (String(rawNode?.semantic_type || "").toLowerCase() === "floor") continue;
    const roomId = roomIdForReplayNode(rawNode, rawNodeById, containsBySource);
    const roomRaw = rawNodeById.get(roomId);
    const layout = normalizeRectLayoutForReplay(rawNode?.layout);
    visibleNodeObjects.push({
      id,
      label: replayNodeLabel(rawNode),
      kind,
      x: layout ? layout.x + layout.w / 2 : 0,
      y: layout ? layout.y + layout.h / 2 : 0,
      width: layout ? layout.w : 0,
      height: layout ? layout.h : 0,
      is_agent_room: false,
      room_id: roomId,
      room_label: roomRaw ? replayNodeLabel(roomRaw) : "",
      layout,
      meta: {
        node_type: rawNode?.node_type || "",
        semantic_class: rawNode?.semantic_class || "",
        semantic_type: rawNode?.semantic_type || "",
        mobility: rawNode?.mobility || "",
        states: cloneData(rawNode?.states || {}) || {},
        property: cloneData(rawNode?.property || {}) || {},
        affordance_count: Number(rawNode?.affordance_count) || 0,
        parent: rawNode?.parent ?? null,
        child: cloneData(rawNode?.child || []) || [],
        interactive_actions: cloneData(rawNode?.interactive_actions || []) || [],
        current_location: rawNode?.current_location ?? null,
        runtime: cloneData(rawNode?.runtime || {}) || {},
      },
    });
  }

  const replayAgentId = String(rawScene?.agent?.id || replayPayload?.summary?.agent_id || "robot_01");
  let agentNode = visibleNodeObjects.find((node) => node.id === replayAgentId);
  if (!agentNode) {
    agentNode = visibleNodeObjects.find((node) => node.kind === "agent");
  }
  if (!agentNode) {
    const currentRoom = String(rawScene?.agent?.current_room || stepPayload?.observation?.robot?.current_room || roomNodes[0]?.id || "");
    const roomRaw = rawNodeById.get(currentRoom);
    agentNode = {
      id: replayAgentId,
      label: state.lang === "cn" ? "机器人" : "Robot",
      kind: "agent",
      x: 0,
      y: 0,
      width: 0,
      height: 0,
      room_id: currentRoom,
      room_label: roomRaw ? replayNodeLabel(roomRaw) : "",
      layout: null,
      meta: {
        node_type: "agent",
        semantic_class: "agent",
        semantic_type: "robot",
        mobility: "mobile",
        states: {},
        property: {},
        affordance_count: 0,
        parent: currentRoom || null,
        child: [],
        interactive_actions: [],
        current_location: currentRoom || null,
      },
    };
    visibleNodeObjects.push(agentNode);
  }

  for (const node of visibleNodeObjects) {
    if (node.kind === "room") {
      node.is_agent_room = node.id === agentNode?.room_id;
    }
  }

  const floorViews = {};
  for (const floor of floors) {
    const floorId = floor.id;
    const floorNode = rawNodeById.get(floorId);
    const floorNodeIds = new Set(
      visibleNodeObjects
        .filter((node) => {
          if (node.kind === "room") return roomFloorMap.get(node.id) === floorId;
          return roomFloorMap.get(node.room_id) === floorId || (!node.room_id && floors.length === 1);
        })
        .map((node) => node.id)
    );
    const nodes = visibleNodeObjects.filter((node) => floorNodeIds.has(node.id));
    const edges = sceneEdges
      .filter((edge) => floorNodeIds.has(String(edge.source_id || "")) && floorNodeIds.has(String(edge.target_id || "")))
      .map((edge) => ({
        source: String(edge.source_id || ""),
        target: String(edge.target_id || ""),
        kind: replayEdgeKind(edge),
        meta: {
          relation: String(edge.relation || ""),
          edge_type: String(edge.edge_type || ""),
          category: String(edge.category || ""),
          properties: cloneData(edge.properties || {}) || {},
        },
      }));
    floorViews[floorId] = {
      floor_id: floorId,
      floor_name: floor.name,
      node_count: nodes.length,
      edge_count: edges.length,
      layout_mode: nodes.some((node) => node.kind === "room" && node.layout) ? "floorplan" : "graph",
      floorplan_bounds: normalizeRectLayoutForReplay(floorNode?.layout),
      nodes,
      edges,
    };
  }

  const worldState = rawScene?.world_state || {};
  const day = Number(worldState.day) || 1;
  const currentStep = Number(worldState.step) || stepIndex || 0;
  const minutesPerStep = Math.max(1, Number(worldState.minutes_per_step) || 10);
  const currentRoom = String(rawScene?.agent?.current_room || agentNode?.room_id || roomNodes[0]?.id || "");
  const currentRoomRaw = rawNodeById.get(currentRoom);
  const currentFloor = roomFloorMap.get(currentRoom) || floors[0]?.id || "F1";
  const sceneMetrics = cloneData(stepPayload?.scene_metrics || replayPayload?.run?.final_metrics || {}) || {};
  const worldMetrics = cloneData(sceneMetrics.world_metrics || {}) || {};
  const roleMetrics = cloneData(sceneMetrics.role_metrics || {}) || {};
  const topIssues = cloneData(sceneMetrics.top_issues || []) || [];
  const totalSteps = Number(replayPayload?.summary?.step_count) || Number(replayPayload?.run?.steps?.length) || 1;

  return {
    scene: {
      id: String(replayPayload?.scene_id || rawScene?.scene_name || "replay_scene"),
      name: state.lang === "cn"
        ? String(rawScene?.scene_name_cn || rawScene?.scene_name || replayPayload?.scene_id || "回放场景")
        : String(rawScene?.scene_name || rawScene?.scene_name_cn || replayPayload?.scene_id || "Replay Scene"),
      floor_count: floors.length,
      room_count: roomNodes.length,
      object_count: Math.max(0, visibleNodeObjects.length - roomNodes.length),
      path: "",
    },
    agent: {
      id: agentNode?.id || replayAgentId,
      current_room: currentRoom,
      current_room_label: currentRoomRaw ? replayNodeLabel(currentRoomRaw) : currentRoom,
      current_floor: currentFloor,
      inventory: cloneData(rawScene?.agent?.inventory || []) || [],
    },
    floors,
    current_floor: currentFloor,
    floor_views: floorViews,
    timeline: {
      day,
      weekday_name: String(worldState.weekday_name || ""),
      weekday_name_cn: String(worldState.weekday_name_cn || ""),
      season_name: String(worldState.season_name || ""),
      season_name_cn: String(worldState.season_name_cn || ""),
      weather: String(worldState.weather || ""),
      collapse_stage: String(worldState.collapse_stage || ""),
      entropy: Number(worldState.entropy) || 0,
      current_step: currentStep,
      start_time_min: Number(worldState.time_min) || 0,
      minutes_per_step: minutesPerStep,
      max_step: Math.max(currentStep, totalSteps - 1),
    },
    scene_metrics: sceneMetrics,
    world_metrics: worldMetrics,
    role_metrics: roleMetrics,
    top_issues: topIssues,
  };
}

function replaySummaryText(replay) {
  if (!replay) return t().replayStatusReady;
  const summary = replay.summary || {};
  const terminated = summary.terminated ? t().replayTerminated : t().replayNotTerminated;
  const reason = summary.termination_reason ? ` · ${summary.termination_reason}` : "";
  return `${replay.scene_id} · ${replayExperimentLabel(summary)} · ${terminated}${reason}`;
}

async function openReplayAnalysis() {
  const sourceSceneId = String(state.replay.sourceSceneId || state.currentScene?.scene?.id || "");
  const related = (state.replay.list || []).filter((item) => String(item.scene_id || "") === sourceSceneId);
  if (!related.length) {
    openMetricsWindow(t().replayAnalysisTitle, `<div class="metric-empty">${t().replayAnalysisEmpty}</div>`);
    return;
  }
  const payloads = await Promise.all(
    related.map(async (item) => {
      const replayId = String(item.replay_id || "");
      const res = await fetch(`/api/replay_metrics/${encodeURIComponent(replayId)}`);
      if (!res.ok) return null;
      const metrics = await res.json();
      const series = Array.isArray(metrics.series) ? metrics.series : [];
      return {
        replayId,
        title: `${replayExperimentLabel(item)} · ${formatMetricValue(item.final_world_score)}`,
        meta: `${String(item.created_at || "")} · steps ${String(item.step_count ?? 0)}`,
        label: `${replayExperimentLabel(item)} · ${formatMetricValue(item.final_world_score)}`,
        values: series.map((point) => Number(point.world_score) || 0),
        finalScore: Number(item.final_world_score) || 0,
        context: series.map((point) => ({
          season: String(point.season_name_cn || point.season_name || ""),
          weekday: String(point.weekday_name_cn || point.weekday_name || ""),
        })),
      };
    })
  );
  state.replay.analysisCandidates = payloads.filter(Boolean);
  const previousSelected = new Set((state.replay.analysisSelectedIds || []).map(String));
  const nextSelected = state.replay.analysisCandidates
    .map((item) => String(item.replayId))
    .filter((replayId) => previousSelected.has(replayId));
  state.replay.analysisSelectedIds = nextSelected.length ? nextSelected : replayAnalysisDefaults(state.replay.analysisCandidates);
  const markup = renderReplayAnalysisMarkup();
  openMetricsWindow(t().replayAnalysisTitle, markup);
  bindReplayAnalysisControls();
}

function renderReplaySummaryBar() {
  replaySummaryBar.textContent = state.replay.loading ? t().replayLoading : replaySummaryText(state.replay.current);
}

function replayCard(title, value) {
  return `
    <div class="replay-step-card">
      <div class="replay-step-label">${title}</div>
      <div class="replay-step-value">${escapeHtml(value)}</div>
    </div>
  `;
}

function renderReplayStepPanel() {
  const step = replayCurrentStep();
  if (!step) {
    replayStepPanel.textContent = t().currentActionEmpty;
    return;
  }
  replayStepPanel.innerHTML = [
    replayCard(t().currentActionReasoning, typeof step.reasoning === "string" ? step.reasoning : JSON.stringify(step.reasoning || {}, null, 2)),
    replayCard(t().currentActionAction, JSON.stringify(step.action || {}, null, 2)),
    replayCard(t().currentActionStatus, step.ok ? "OK" : "FAILED"),
  ].join("");
}

function renderReplayReadout() {
  const replay = state.replay.current;
  const step = replayCurrentStep();
  if (!replay || !step) {
    replayReadout.textContent = t().replayNoSelection;
    replaySlider.max = "0";
    replaySlider.value = "0";
    return;
  }
  const total = Number(replay.summary?.step_count) || replay.run?.steps?.length || 0;
  replaySlider.max = String(Math.max(0, total - 1));
  replaySlider.value = String(state.replay.stepIndex);
  const worldState = step.scene?.world_state || {};
  const text = t().replayStatusBar
    .replace("{step}", String(state.replay.stepIndex + 1))
    .replace("{max}", String(total))
    .replace("{day}", String(Number(worldState.day) || 1))
    .replace("{clock}", formatClockFromScene(step.scene))
    .replace("{score}", formatMetricValue(step.world_score));
  replayReadout.textContent = text;
}

function renderReplayList() {
  replayList.innerHTML = "";
  if (!state.replay.list.length) {
    replayList.innerHTML = `<div class="replay-item"><div class="replay-item-meta">${escapeHtml(t().replayEmptyList)}</div></div>`;
    return;
  }
  for (const item of state.replay.list) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `replay-item ${item.replay_id === state.replay.currentId ? "active" : ""}`;
    button.innerHTML = `
      <div class="replay-item-title">${escapeHtml(item.scene_id || item.replay_id)}</div>
      <div class="replay-item-meta">
        ID: ${escapeHtml(item.replay_id || "")}<br />
        ${escapeHtml(item.created_at || "")}<br />
        ${escapeHtml(replayExperimentLabel(item))} · steps ${escapeHtml(item.step_count ?? 0)}<br />
        world ${escapeHtml(formatMetricValue(item.final_world_score))}${item.termination_reason ? ` · ${escapeHtml(item.termination_reason)}` : ""}
      </div>
    `;
    button.addEventListener("click", () => loadReplay(item.replay_id).catch(console.error));
    replayList.appendChild(button);
  }
}

function applyReplayScene(adaptedScene) {
  state.currentScene = adaptedScene;
  state.currentFloorId = adaptedScene.current_floor || adaptedScene.floors?.[0]?.id || null;
  state.graphFlowFitNonce = (state.graphFlowFitNonce || 0) + 1;
  state.timeline = timelineStateFromScene(adaptedScene);
  state.lastRenderedMode = null;
  state.layoutViews = {};
  state.expandedNodes = new Set();
  return buildSceneLayouts(state.currentScene).then(() => {
    state.viewBox = computeViewBoxForView(state.layoutViews?.[state.currentFloorId] || state.currentScene.floor_views?.[state.currentFloorId]);
    renderTimeline();
    draw();
  });
}

async function setReplayStep(stepIndex) {
  const replay = state.replay.current;
  const totalSteps = Number(replay?.summary?.step_count) || replay?.run?.steps?.length || 0;
  if (!totalSteps) return;
  const nextIndex = clamp(Math.round(Number(stepIndex) || 0), 0, totalSteps - 1);
  state.replay.stepIndex = nextIndex;
  if (!state.replay.stepCache[nextIndex]) {
    const res = await fetch(`/api/replay/${encodeURIComponent(replay.replay_id || replayIdForReplay())}/step/${encodeURIComponent(nextIndex)}`);
    if (!res.ok) throw new Error(`Failed to load replay step ${nextIndex}`);
    const payload = await res.json();
    if (payload?.step) {
      state.replay.stepCache[nextIndex] = payload.step;
    }
  }
  const stepPayload = state.replay.stepCache[nextIndex];
  const adaptedScene = adaptReplayScene(stepPayload.scene, replay, nextIndex, stepPayload);
  await applyReplayScene(adaptedScene);
  renderReplaySummaryBar();
  renderReplayReadout();
  renderReplayStepPanel();
  renderReplayList();
}

function playReplay() {
  const total = Number(state.replay.current?.summary?.step_count) || state.replay.current?.run?.steps?.length || 0;
  if (!total || state.replay.stepIndex >= total - 1) {
    renderReplayReadout();
    return;
  }
  if (state.replay.playing) return;
  state.replay.playing = true;
  const playSeq = (state.replay.playSeq || 0) + 1;
  state.replay.playSeq = playSeq;
  const tick = () => {
    if (state.replay.playSeq !== playSeq) return;
    state.replay.timer = null;
    if (!state.replay.playing) return;
    const maxIndex = (Number(state.replay.current?.summary?.step_count) || state.replay.current?.run?.steps?.length || 1) - 1;
    if (state.replay.stepIndex >= maxIndex) {
      stopReplayPlayback();
      return;
    }
    setReplayStep(state.replay.stepIndex + 1)
      .then(() => {
        if (!state.replay.playing || state.replay.playSeq !== playSeq) return;
        state.replay.timer = window.setTimeout(tick, replayDelayMs());
      })
      .catch((error) => {
        console.error(error);
        stopReplayPlayback();
      });
  };
  state.replay.timer = window.setTimeout(tick, replayDelayMs());
}

async function loadReplayList() {
  const res = await fetch("/api/replays");
  if (!res.ok) throw new Error(t().replayListLoadFail);
  const payload = await res.json();
  state.replay.list = Array.isArray(payload.replays) ? payload.replays : [];
  renderReplayList();
  renderReplaySummaryBar();
}

async function loadModelOptions() {
  try {
    const res = await fetch("/api/models");
    if (!res.ok) throw new Error("Failed to load models");
    const payload = await res.json();
    state.modelOptions = Array.isArray(payload.models) ? payload.models.filter(Boolean) : [];
  } catch (error) {
    console.error(error);
    state.modelOptions = [];
  }
  renderModelOptions();
}

async function loadReplay(replayId) {
  stopTimelinePlayback();
  stopReplayPlayback();
  setUiMode("replay");
  state.replay.loading = true;
  state.replay.currentId = replayId;
  state.replay.stepCache = {};
  state.replay.metricSeries = [];
  renderReplaySummaryBar();
  replayReadout.textContent = t().replayLoading;
  try {
    const [res, metricsRes] = await Promise.all([
      fetch(`/api/replay/${encodeURIComponent(replayId)}?summary=1`),
      fetch(`/api/replay_metrics/${encodeURIComponent(replayId)}`),
    ]);
    if (!res.ok) {
      throw new Error(`Failed to load replay ${replayId}`);
    }
    const payload = await res.json();
    const metricPayload = metricsRes.ok ? await metricsRes.json() : { series: [] };
    state.replay.current = payload;
    state.replay.currentId = String(payload.replay_id || replayId);
    state.replay.sourceSceneId = String(payload.scene_id || "");
    state.replay.stepIndex = 0;
    state.replay.metricSeries = Array.isArray(metricPayload.series) ? metricPayload.series : [];
    await setReplayStep(0);
  } catch (error) {
    state.replay.loading = false;
    replaySummaryBar.textContent = error.message || String(error);
    replayReadout.textContent = error.message || String(error);
    throw error;
  }
  state.replay.loading = false;
  renderReplaySummaryBar();
  renderReplayReadout();
  renderReplayList();
}

async function runReplay() {
  stopReplayPlayback();
  if ((replayRunExperiment.value || "full_agent") === "pure_human") {
    await startHumanSession();
    return;
  }
  replaySummaryBar.textContent = t().replayRunning;
  const body = {
    scene_id: replayRunScene.value,
    experiment_type: replayRunExperiment.value || "full_agent",
    agent_id: replayRunAgent.value || "robot_01",
    agent_model: replayRunModel.value || "bailian-qwen3.5-flash",
    max_days: Number(replayRunDays.value) || 7,
    timeout: Number(replayRunTimeout.value) || 30,
  };
  replayRunButton.disabled = true;
  try {
    const res = await fetch("/api/replays/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errorPayload = await res.json().catch(() => ({}));
      throw new Error(errorPayload.error || "Failed to run replay");
    }
    const payload = await res.json();
    await loadReplayList();
    await loadReplay(String(payload.replay_id || ""));
  } finally {
    replayRunButton.disabled = false;
  }
}

function memoryEdgeKey(edge) {
  return [
    String(edge?.source_id || edge?.source || ""),
    String(edge?.relation || edge?.kind || ""),
    String(edge?.target_id || edge?.target || ""),
  ].join("::");
}

function memoryContainsEdgeKey(source, target) {
  return memoryEdgeKey({ source, relation: "contains", target });
}

function restrictSceneToCurrentRoom(scenePayload, observation, memoryGraph = {}) {
  if (!scenePayload || !observation) return scenePayload;
  const currentRoom = String(observation?.robot?.current_room || scenePayload?.agent?.current_room || "");
  const visibleIds = new Set([currentRoom, String(scenePayload?.agent?.id || "robot_01")]);
  for (const nodeId of memoryGraph.node_ids || []) {
    if (nodeId) visibleIds.add(String(nodeId));
  }
  for (const node of observation.visible_nodes || []) visibleIds.add(String(node.id || ""));
  const memoryEdges = new Set((memoryGraph.edges || []).map(memoryEdgeKey));
  const next = cloneData(scenePayload);
  const floorId = String(next.current_floor || "");
  const view = next.floor_views?.[floorId];
  if (view) {
    view.nodes = (view.nodes || []).filter((node) => visibleIds.has(String(node.id || "")));
    view.edges = (view.edges || []).filter(
      (edge) => {
        if (!visibleIds.has(String(edge.source || "")) || !visibleIds.has(String(edge.target || ""))) return false;
        if (!memoryEdges.size) return true;
        const relation = String(edge?.meta?.relation || edge.kind || "");
        if (memoryEdges.has(memoryEdgeKey({ source: edge.source, relation, target: edge.target }))) return true;
        if (edge.kind === "contains") {
          return memoryEdges.has(memoryContainsEdgeKey(edge.source, edge.target));
        }
        if (edge.kind === "neighbor") {
          return memoryEdges.has(memoryEdgeKey({ source: edge.target, relation, target: edge.source }));
        }
        return false;
      }
    );
    const agentId = String(scenePayload?.agent?.id || observation?.robot?.id || "robot_01");
    const agentNode = (view.nodes || []).find((node) => String(node.id || "") === agentId);
    const agentParent = String(agentNode?.meta?.parent || "");
    const agentAnchor = agentParent && visibleIds.has(agentParent) ? agentParent : currentRoom;
    const hasAgentEdge = (view.edges || []).some(
      (edge) => String(edge.target || "") === agentId || String(edge.source || "") === agentId
    );
    const hasAgentAnchor = (view.nodes || []).some((node) => String(node.id || "") === agentAnchor);
    const hasAgentNode = (view.nodes || []).some((node) => String(node.id || "") === agentId);
    if (agentAnchor && agentId && hasAgentAnchor && hasAgentNode && !hasAgentEdge) {
      view.edges.push({
        source: agentAnchor,
        target: agentId,
        kind: "agent_at",
        meta: {
          relation: agentAnchor === currentRoom ? "at" : "near",
          edge_type: "runtime_edge",
          category: "runtime",
          properties: { synthetic: true },
        },
      });
    }
    view.node_count = view.nodes.length;
    view.edge_count = view.edges.length;
  }
  next.floors = (next.floors || []).filter((floor) => String(floor.id || "") === floorId);
  const roomCount = (view?.nodes || []).filter((node) => String(node.kind || "") === "room").length;
  const objectCount = (view?.nodes || []).filter((node) => String(node.kind || "") !== "room" && String(node.kind || "") !== "agent").length;
  next.scene.floor_count = 1;
  next.scene.room_count = roomCount;
  next.scene.object_count = objectCount;
  return next;
}

function humanSessionScene(sessionPayload) {
  const stepPayload = cloneData(sessionPayload.current_step || {});
  const replayPayload = {
    replay_id: String(sessionPayload.replay_id || ""),
    scene_id: String(sessionPayload.scene_id || ""),
    summary: cloneData(sessionPayload.summary || {}),
    run: { steps: [] },
  };
  const sourceScene = stepPayload.memory_scene || stepPayload.scene || {};
  const adapted = adaptReplayScene(sourceScene, replayPayload, Number(stepPayload.episode_step || 0), stepPayload);
  return restrictSceneToCurrentRoom(adapted, stepPayload.observation || {}, sessionPayload.memory_graph || {});
}

function summarizeHumanSession(sessionPayload) {
  const step = sessionPayload?.current_step || {};
  const observation = step?.observation || {};
  const world = observation?.world || {};
  const robot = observation?.robot || {};
  const room = robot?.current_room || "unknown";
  const stepIdx = Number(sessionPayload?.summary?.step_count || 0);
  const maxSteps = Number(sessionPayload?.max_steps || 215);
  const score = Number(step?.world_score || 0).toFixed(3);
  return `Step ${stepIdx}/${maxSteps} · ${world.clock || ""} · room ${room} · world ${score}`;
}

function renderHumanControls() {
  if (!humanControlCard) return;
  const session = state.human.session;
  humanControlCard.classList.toggle("is-hidden", state.uiMode === "replay" || !session);
  if (!session) {
    if (humanSummaryBar) humanSummaryBar.textContent = t().humanNoSession;
    if (humanActionTypes) humanActionTypes.innerHTML = "";
    if (humanActionCandidates) humanActionCandidates.innerHTML = "";
    return;
  }
  if (humanSummaryBar) {
    const error = String(session.validation_error || "");
    humanSummaryBar.textContent = error ? `${t().humanValidationPrefix}${error}` : summarizeHumanSession(session);
  }
  if (humanActionHint) humanActionHint.textContent = t().humanActionHint;
  const candidates = Array.isArray(session.action_candidates) ? session.action_candidates : [];
  const grouped = {};
  for (const actionType of ["move", "pick", "place", "press", "scan", "open", "close", "brush"]) grouped[actionType] = [];
  for (const item of candidates) {
    const key = String(item.action_type || "");
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(item);
  }
  const preferredActionType = grouped.move?.length
    ? "move"
    : Object.keys(grouped).find((actionType) => (grouped[actionType] || []).length) || "move";
  if (!(grouped[state.human.selectedActionType] || []).length) {
    state.human.selectedActionType = preferredActionType;
  }
  if (humanActionTypes) {
    humanActionTypes.innerHTML = "";
    for (const actionType of Object.keys(grouped)) {
      const btn = document.createElement("button");
      btn.className = `human-action-type ${state.human.selectedActionType === actionType ? "active" : ""}`;
      btn.type = "button";
      btn.textContent = `${actionType} (${grouped[actionType].length})`;
      btn.title = grouped[actionType][0]?.effect_preview || actionType;
      btn.addEventListener("mouseenter", () => {
        if (humanActionHint) humanActionHint.textContent = grouped[actionType][0]?.effect_preview || actionType;
      });
      btn.addEventListener("click", () => {
        state.human.selectedActionType = actionType;
        renderHumanControls();
      });
      humanActionTypes.appendChild(btn);
    }
  }
  if (humanActionCandidates) {
    const selected = grouped[state.human.selectedActionType] || [];
    humanActionCandidates.innerHTML = "";
    if (!selected.length) {
      humanActionCandidates.innerHTML = `<div class="panel-subtitle">${t().humanNoCandidates}</div>`;
    } else {
      for (const item of selected) {
        const btn = document.createElement("button");
        btn.className = "human-action-candidate";
        btn.type = "button";
        const label = String(item.target_id || item.placement_target_id || item.object_id || "");
        btn.innerHTML = `<div>${escapeHtml(label)}</div><small>${escapeHtml(String(item.effect_preview || ""))}</small>`;
        btn.title = String(item.effect_preview || "");
        btn.addEventListener("mouseenter", () => {
          if (humanActionHint) humanActionHint.textContent = String(item.effect_preview || "");
        });
        btn.addEventListener("click", () => applyHumanAction(item).catch(console.error));
        humanActionCandidates.appendChild(btn);
      }
    }
  }
}

async function startHumanSession() {
  stopTimelinePlayback();
  const body = {
    scene_id: replayRunScene.value,
    agent_id: replayRunAgent.value || "robot_01",
  };
  replayRunButton.disabled = true;
  try {
    const res = await fetch("/api/human_sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error || "Failed to start human session");
    state.human.session = payload;
    state.human.selectedActionType = "move";
    state.currentScene = humanSessionScene(payload);
    state.currentFloorId = state.currentScene.current_floor;
    state.timeline = timelineStateFromScene(state.currentScene);
    state.layoutViews = {};
    await buildSceneLayouts(state.currentScene);
	    state.viewBox = computeViewBoxForView(state.layoutViews?.[state.currentFloorId] || state.currentScene.floor_views?.[state.currentFloorId]);
	    renderTimeline();
	    draw();
	    renderHumanControls();
	    setUiMode("scene");
	  } finally {
	    replayRunButton.disabled = false;
	  }
	}

async function applyHumanAction(candidate) {
  const sessionId = String(state.human.session?.session_id || "");
  if (!sessionId) return;
  const res = await fetch(`/api/human_sessions/${encodeURIComponent(sessionId)}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(candidate || {}),
  });
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || "Failed to apply human action");
  state.human.session = payload;
  state.human.selectedActionType = "move";
  state.currentScene = humanSessionScene(payload);
  state.currentFloorId = state.currentScene.current_floor;
  state.timeline = timelineStateFromScene(state.currentScene);
  await buildSceneLayouts(state.currentScene);
  state.viewBox = computeViewBoxForView(state.layoutViews?.[state.currentFloorId] || state.currentScene.floor_views?.[state.currentFloorId]);
  renderTimeline();
  draw();
  renderHumanControls();
  if (payload.terminated) {
    await loadReplayList().catch(console.error);
  }
}

async function endHumanSession() {
  const sessionId = String(state.human.session?.session_id || "");
  if (!sessionId) return;
  const res = await fetch(`/api/human_sessions/${encodeURIComponent(sessionId)}/end`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "human_stopped" }),
  });
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || "Failed to end human session");
  state.human.session = payload;
  renderHumanControls();
  await loadReplayList().catch(console.error);
}

function timelineDelayMs(speed) {
  const normalized = Math.max(1, Number(speed) || 1);
  if (normalized >= 100) return 5;
  if (normalized >= 10) return 50;
  if (normalized >= 3) return 180;
  return 500;
}

async function refreshSceneAtStep(step) {
  if (!state.currentScene?.scene?.id) return;
  const requestSeq = (state.timeline.requestSeq || 0) + 1;
  state.timeline.requestSeq = requestSeq;
  state.timeline.pending = true;
  const sceneId = state.currentScene.scene.id;
  const res = await fetch(
    `/api/scene/${encodeURIComponent(sceneId)}?lang=${encodeURIComponent(state.lang)}&step=${encodeURIComponent(step)}`
  );
  if (!res.ok) {
    if (state.timeline.requestSeq === requestSeq) {
      state.timeline.pending = false;
    }
    throw new Error(`Failed to refresh scene ${sceneId} at step ${step}`);
  }
  const nextScene = await res.json();
  if (state.timeline.requestSeq !== requestSeq) {
    return;
  }
  state.currentScene = nextScene;
  recordMetricSnapshot(state.currentScene);
  state.currentFloorId = nextScene.current_floor || state.currentFloorId;
  const resolvedStep = Number(nextScene.timeline?.current_step);
  state.timeline = {
    ...state.timeline,
    currentStep: Number.isFinite(resolvedStep) ? resolvedStep : step,
    maxStep: Math.max(Number.isFinite(resolvedStep) ? resolvedStep : step, Number(nextScene.timeline?.max_step) || 0),
    day: Number(nextScene.timeline?.day) || state.timeline.day,
    weekdayName: String(nextScene.timeline?.weekday_name_cn || nextScene.timeline?.weekday_name || state.timeline.weekdayName || ""),
    seasonName: String(nextScene.timeline?.season_name_cn || nextScene.timeline?.season_name || state.timeline.seasonName || ""),
    weather: String(nextScene.timeline?.weather || state.timeline.weather || ""),
    collapseStage: String(nextScene.timeline?.collapse_stage || state.timeline.collapseStage || ""),
    entropy: Number(nextScene.timeline?.entropy) || state.timeline.entropy || 0,
    startTimeMin: Number(nextScene.timeline?.start_time_min) || state.timeline.startTimeMin,
    minutesPerStep: Math.max(1, Number(nextScene.timeline?.minutes_per_step) || state.timeline.minutesPerStep),
    pending: false,
  };
  await buildSceneLayouts(state.currentScene);
}

function applyTemporalProfile(node) {
  if (node.kind !== "fixture" && node.kind !== "movable") return node;
  const next = { ...node, meta: cloneData(node.meta || {}) || {} };
  const baseStates = cloneData(next.meta.states || {}) || {};
  const profile = next.meta.temporal_profile || null;
  next.meta.states = baseStates;
  delete next.temporalClass;
  delete next.overlayStateClass;
  delete next.overlayLevel;
  delete next.flashOnStart;
  if (profile?.changes_with_time && profile.update_mode === "decay") {
    const decay = Number(profile.decay_per_step) || 0;
    const thresholds = profile.thresholds || {};
    const initialVitality = Number(baseStates.vitality);
    if (Number.isFinite(initialVitality)) {
      const vitality = clamp(initialVitality - decay * state.timeline.currentStep, 0, 1);
      next.meta.states.vitality = Number(vitality.toFixed(2));
      if (typeof thresholds.fresh === "number" && vitality >= thresholds.fresh) {
        next.meta.states.life_state = "fresh";
      } else if (typeof thresholds.wilted === "number" && vitality <= thresholds.wilted) {
        next.meta.states.life_state = "wilted";
      }
      next.temporalClass = next.meta.states.life_state === "wilted" ? "temporal-wilted" : "temporal-fresh";
    }
  }
  if (profile?.changes_with_time && profile.update_mode === "cycle" && baseStates.running) {
    const durations = profile.durations || {};
    const phases = [
      ["wash", Number(durations.wash) || 0],
      ["spin", Number(durations.spin) || 0],
    ].filter(([, duration]) => duration > 0);
    const total = phases.reduce((sum, [, duration]) => sum + duration, 0);
    if (total > 0) {
      const stepInCycle = state.timeline.currentStep % total;
      let offset = 0;
      for (const [phase, duration] of phases) {
        if (stepInCycle < offset + duration) {
          next.meta.states.cycle_state = phase;
          next.meta.states.cycle_remaining_step = offset + duration - stepInCycle;
          break;
        }
        offset += duration;
      }
      next.temporalClass = "temporal-running";
    }
  }
  const states = next.meta.states || {};
  const semantic = semanticTypeOf(next);
  const hasExplicitPowerState = ("running" in states) || ("is_on" in states);
  const applianceActiveFirst = states.running || states.is_on;
  const powerFirstSemantics = new Set([
    "refrigerator",
    "fridge",
    "medicine_fridge",
    "washer",
    "washing_machine",
    "dishwasher",
    "microwave",
    "stove",
    "sink",
  ]);
  const cycleTotal = temporalCycleTotal(profile);
  const runningOverlayEligible = powerFirstSemantics.has(semantic) && applianceActiveFirst;
  if (states.spoilage === "spoiled" || states.is_spoiled) {
    next.temporalClass = "state-spoiled";
  } else if (states.is_open || states.isOpen || states.door_open) {
    next.temporalClass = "state-open";
  } else if (runningOverlayEligible) {
    next.overlayStateClass = "state-on";
    next.overlayLevel = temporalOverlayLevel(states, cycleTotal);
    next.flashOnStart = registerDeviceActivity(next.id, true);
  } else if (powerFirstSemantics.has(semantic) && hasExplicitPowerState && !applianceActiveFirst) {
    next.temporalClass = "";
  } else if (states.temperature === "cold") {
    next.temporalClass = "state-cold";
  } else if (states.temperature === "warm" || states.temperature === "hot") {
    next.temporalClass = "state-warm";
  } else if (states.running || states.is_on) {
    next.temporalClass = "state-on";
  } else if (states.is_dirty || states.is_clean === false || states.scattered) {
    next.temporalClass = "state-dirty";
  } else if (
    states.is_full ||
    (typeof states.fill_level === "number" && states.fill_level > 0) ||
    typeof states.cleanliness === "number" && states.cleanliness <= 0.6
  ) {
    next.temporalClass = "state-full";
  }
  if (!runningOverlayEligible) {
    registerDeviceActivity(next.id, false);
  }
  return next;
}

function temporalCycleTotal(profile) {
  const durations = profile?.durations || {};
  const wash = Number(durations.wash) || 0;
  const spin = Number(durations.spin) || 0;
  const total = wash + spin;
  return total > 0 ? total : 0;
}

function temporalOverlayLevel(states, totalSteps) {
  if (typeof states.cycle_remaining_step === "number" && states.cycle_remaining_step > 0 && totalSteps > 0) {
    return clamp(states.cycle_remaining_step / totalSteps, 0, 1);
  }
  return 1;
}

function registerDeviceActivity(nodeId, active) {
  const step = Number(state.timeline.currentStep) || 0;
  const previous = state.deviceActivity[nodeId];
  const isNewStart = active && (!previous || !previous.active);
  state.deviceActivity[nodeId] = { active, step };
  return isNewStart;
}

function renderNodeInfo(node, options = {}) {
  const { preserveSelection = false } = options;
  if (!node) {
    if (!preserveSelection) {
      state.selectedNodeId = null;
      state.selectedNodeSnapshot = null;
    }
    nodeInfo.textContent = t().emptyInfo;
    return;
  }
  state.selectedNodeSnapshot = cloneData(node);
  const roomText = node.room_id ? (node.room_label || node.room_id) : "";
  const unavailableHint = preserveSelection ? `<div class="node-hint">${t().nodeUnavailable}</div>` : "";
  nodeInfo.innerHTML = `<div><strong>${node.label}</strong></div><div class="node-hint">ID: ${node.id}</div><div class="node-hint">${t().kind}：${kindLabel(node.kind)}${node.room_id ? ` | ${t().room}：${roomText}` : ""}</div>${unavailableHint}<pre>${JSON.stringify(node.meta ?? {}, null, 2)}</pre>`;
}

function info(node) {
  if (Date.now() < state.suppressClickUntil) return;
  if (!node) {
    renderNodeInfo(null);
    return;
  }
  state.selectedNodeId = node.id || null;
  renderNodeInfo(node);
}

function pickStateKeys(states) {
  if (!states || typeof states !== "object") return {};
  const keys = [
    "current_activity",
    "mood",
    "is_open",
    "is_on",
    "running",
    "cycle_state",
    "cycle_remaining_step",
    "temperature",
    "fill_level",
    "is_full",
    "cleanliness",
    "is_dirty",
    "is_clean",
    "scattered",
    "spoilage",
    "is_spoiled",
    "life_state",
    "vitality",
  ];
  const out = {};
  for (const key of keys) {
    if (key in states) out[key] = states[key];
  }
  return out;
}

function tooltipHtml(node) {
  const nodeType = nodeTypeOf(node);
  const semantic = semanticTypeOf(node);
  const states = node?.meta?.states || {};
  const picked = pickStateKeys(states);
  const room = node.room_label || node.room_id || "";
  const metaLine = [nodeType || node.kind || "", semantic || "", room ? `@ ${room}` : ""].filter(Boolean).join(" · ");
  const kv = Object.keys(picked).length ? JSON.stringify(picked, null, 0) : "{}";
  return `
    <div class="tt-title">${escapeHtml(node.label || node.id || "")}</div>
    <div class="tt-meta">${escapeHtml(metaLine)}</div>
    <div class="tt-kv">${escapeHtml(kv)}</div>
  `;
}

function escapeHtml(raw) {
  return String(raw)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function positionTooltip(clientX, clientY) {
  if (!hoverTooltip) return;
  const stage = graphSvg.parentElement;
  const rect = stage.getBoundingClientRect();
  const padding = 12;
  const maxLeft = rect.width - padding;
  const maxTop = rect.height - padding;
  const localX = clientX - rect.left;
  const localY = clientY - rect.top;
  const left = clamp(localX + 14, padding, maxLeft);
  const top = clamp(localY + 14, padding, maxTop);
  hoverTooltip.style.left = `${left}px`;
  hoverTooltip.style.top = `${top}px`;
}

function showHoverTooltip(node, clientX, clientY) {
  if (!hoverTooltip) return;
  state.hover.nodeId = node?.id || null;
  state.hover.clientX = clientX;
  state.hover.clientY = clientY;
  hoverTooltip.hidden = false;
  hoverTooltip.innerHTML = tooltipHtml(node);
  positionTooltip(clientX, clientY);
}

function updateHoverTooltip(node, clientX, clientY) {
  if (!hoverTooltip || hoverTooltip.hidden) return;
  state.hover.nodeId = node?.id || null;
  state.hover.clientX = clientX;
  state.hover.clientY = clientY;
  hoverTooltip.innerHTML = tooltipHtml(node);
  positionTooltip(clientX, clientY);
}

function hideHoverTooltip() {
  if (!hoverTooltip) return;
  state.hover.nodeId = null;
  hoverTooltip.hidden = true;
}

function findNodeAcrossFloors(nodeId) {
  if (!nodeId || !state.currentScene?.floor_views) return null;
  for (const view of Object.values(state.currentScene.floor_views)) {
    const match = view?.nodes?.find((item) => item.id === nodeId);
    if (match) return match;
  }
  return null;
}

function edgeClass(kind) {
  if (kind === "neighbor") return "edge-neighbor";
  if (kind === "contains") return "edge-contains";
  if (kind === "ontop") return "edge-ontop";
  if (kind === "next_to") return "edge-next_to";
  if (kind === "controls") return "edge-controls";
  if (kind === "transport") return "edge-transport";
  return "edge-other";
}

function isFloorplanView(view) {
  return view?.layout_mode === "floorplan" || (view?.nodes || []).some((node) => node.kind === "room" && node.layout);
}

function normalizeRectLayout(layout) {
  if (!layout || !isFiniteNumber(layout.x) || !isFiniteNumber(layout.y) || !isFiniteNumber(layout.w) || !isFiniteNumber(layout.h)) {
    return null;
  }
  return {
    x: Number(layout.x),
    y: Number(layout.y),
    w: Number(layout.w),
    h: Number(layout.h),
    orientation: layout.orientation || "",
    doorways: Array.isArray(layout.doorways) ? layout.doorways.map((doorway) => ({
      ...doorway,
      to: doorway.to || doorway.target_room || "",
      x: Number(doorway.x),
      y: Number(doorway.y),
      length: Number(doorway.length),
      width: Number(doorway.width),
    })) : [],
  };
}

function floorplanBounds(view) {
  const explicit = normalizeRectLayout(view?.floorplan_bounds);
  if (explicit) return explicit;
  const layouts = (view?.nodes || [])
    .map((node) => normalizeRectLayout(node.layout))
    .filter(Boolean);
  if (!layouts.length) return null;
  const minX = Math.min(...layouts.map((layout) => layout.x));
  const minY = Math.min(...layouts.map((layout) => layout.y));
  const maxX = Math.max(...layouts.map((layout) => layout.x + layout.w));
  const maxY = Math.max(...layouts.map((layout) => layout.y + layout.h));
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}

function computeViewBoxForView(view) {
  if (!isFloorplanView(view)) return { ...defaultViewBox };
  const bounds = floorplanBounds(view);
  if (!bounds) return { ...defaultViewBox };
  const padding = Math.max(bounds.w, bounds.h) * 0.04 + 0.18;
  return {
    x: bounds.x - padding,
    y: bounds.y - padding,
    width: Math.max(4.5, bounds.w + padding * 2),
    height: Math.max(4.5, bounds.h + padding * 2),
  };
}

function resetViewBoxForCurrentFloor() {
  const view = state.layoutViews?.[state.currentFloorId] || state.currentScene?.floor_views?.[state.currentFloorId] || null;
  state.viewBox = computeViewBoxForView(view);
  applyViewBox();
}

function buildChildrenMap(view) {
  const map = new Map();
  for (const node of view.nodes || []) {
    if (Array.isArray(node.meta?.child)) {
      map.set(node.id, [...node.meta.child]);
    }
  }
  for (const edge of view.edges || []) {
    if (edge.kind !== "contains") continue;
    if (!map.has(edge.source)) map.set(edge.source, []);
    map.get(edge.source).push(edge.target);
  }
  for (const [key, list] of map) {
    map.set(key, Array.from(new Set(list)));
  }
  return map;
}

function floorplanNodeDiameter(node) {
  if (node.kind === "agent" || nodeTypeOf(node) === "agent") return 0.26;
  if (node.kind === "movable" || nodeTypeOf(node) === "movable_object") return 0.18;
  return 0.2;
}

function resolveRoomId(node, nodeById) {
  if (!node) return "";
  if (node.kind === "room") return String(node.id || "");
  if (isRoomDoorNode(node)) {
    const connectedRooms = connectedRoomsForNode(node);
    return connectedRooms[0] || "";
  }
  if (node.room_id) return String(node.room_id);
  let currentId = String(node.meta?.parent || node.parent || "");
  const seen = new Set();
  while (currentId && !seen.has(currentId)) {
    seen.add(currentId);
    const current = nodeById.get(currentId);
    if (!current) break;
    if (current.kind === "room") return String(current.id || "");
    currentId = String(current.meta?.parent || current.parent || "");
  }
  return "";
}

function doorwayPointBetweenRooms(room, otherRoom) {
  const roomLayout = normalizeRectLayout(room?.layout);
  if (!roomLayout || !otherRoom) return null;
  const otherId = String(otherRoom.id || "");
  for (const doorway of roomLayout.doorways || []) {
    if (String(doorway.to || "") !== otherId) continue;
    const horizontal = String(doorway.orientation || "").toLowerCase() === "horizontal";
    return {
      x: horizontal ? doorway.x + doorway.length / 2 : doorway.x,
      y: horizontal ? doorway.y : doorway.y + doorway.length / 2,
    };
  }
  return null;
}

function roomCenterPoint(room) {
  const layout = normalizeRectLayout(room?.layout);
  if (layout) {
    return { x: layout.x + layout.w / 2, y: layout.y + layout.h / 2 };
  }
  if (isFiniteNumber(room?.x) && isFiniteNumber(room?.y)) {
    return { x: Number(room.x), y: Number(room.y) };
  }
  return null;
}

function roomDoorPoint(node, nodeById, edges = []) {
  const nodeId = String(node?.id || "");
  const doorAssignments = buildRoomDoorAssignments(nodeById, edges);
  const assignedEdge = doorAssignments.get(nodeId);
  if (assignedEdge) {
    const sourceRoom = nodeById.get(String(assignedEdge.source || ""));
    const targetRoom = nodeById.get(String(assignedEdge.target || ""));
    const sourceCenter = roomCenterPoint(sourceRoom);
    const targetCenter = roomCenterPoint(targetRoom);
    if (sourceCenter && targetCenter) {
      return {
        x: (sourceCenter.x + targetCenter.x) / 2,
        y: (sourceCenter.y + targetCenter.y) / 2,
      };
    }
  }
  const connectedRooms = connectedRoomsForNode(node);
  if (!connectedRooms.length) return null;
  const anchorRoom = nodeById.get(connectedRooms[0]);
  if (!anchorRoom) return null;
  const runtime = runtimeMetaOf(node);
  const preferredTarget = String(runtime.doorway_to || "");
  const targets = preferredTarget
    ? connectedRooms.filter((roomId) => roomId !== connectedRooms[0] && roomId === preferredTarget)
    : connectedRooms.slice(1);
  for (const targetRoomId of targets) {
    const targetRoom = nodeById.get(targetRoomId);
    const doorwayPoint = doorwayPointBetweenRooms(anchorRoom, targetRoom) || doorwayPointBetweenRooms(targetRoom, anchorRoom);
    if (doorwayPoint) return doorwayPoint;
  }
  const anchorCenter = roomCenterPoint(anchorRoom);
  if (!anchorCenter) return null;
  const targetCenters = connectedRooms
    .slice(1)
    .map((roomId) => roomCenterPoint(nodeById.get(roomId)))
    .filter(Boolean);
  if (!targetCenters.length) return anchorCenter;
  const avgTarget = {
    x: targetCenters.reduce((sum, point) => sum + point.x, 0) / targetCenters.length,
    y: targetCenters.reduce((sum, point) => sum + point.y, 0) / targetCenters.length,
  };
  return {
    x: (anchorCenter.x + avgTarget.x) / 2,
    y: (anchorCenter.y + avgTarget.y) / 2,
  };
}

function buildRoomDoorAssignments(nodeById, edges = []) {
  const neighborEdges = (edges || []).filter((edge) => String(edge?.kind || "") === "neighbor");
  const candidateEdgeIdsByDoor = new Map();
  const edgeById = new Map();

  neighborEdges.forEach((edge, index) => {
    const edgeId = `${String(edge.source || "")}->${String(edge.target || "")}#${index}`;
    edgeById.set(edgeId, edge);
    const props = edge?.meta?.properties || {};
    const doorIds = [];
    const primaryDoorId = String(props.door_id || "");
    if (primaryDoorId) doorIds.push(primaryDoorId);
    for (const doorId of props.door_ids || []) {
      const normalizedDoorId = String(doorId || "");
      if (normalizedDoorId && !doorIds.includes(normalizedDoorId)) {
        doorIds.push(normalizedDoorId);
      }
    }
    for (const doorId of doorIds) {
      if (!candidateEdgeIdsByDoor.has(doorId)) candidateEdgeIdsByDoor.set(doorId, []);
      candidateEdgeIdsByDoor.get(doorId).push(edgeId);
    }
  });

  const doorIds = [...candidateEdgeIdsByDoor.keys()].sort((left, right) => {
    const leftCount = candidateEdgeIdsByDoor.get(left)?.length || 0;
    const rightCount = candidateEdgeIdsByDoor.get(right)?.length || 0;
    return leftCount - rightCount || left.localeCompare(right);
  });

  const matchedDoorByEdgeId = new Map();
  function assignDoor(doorId, visited = new Set()) {
    const candidateEdgeIds = candidateEdgeIdsByDoor.get(doorId) || [];
    for (const edgeId of candidateEdgeIds) {
      if (visited.has(edgeId)) continue;
      visited.add(edgeId);
      const currentDoorId = matchedDoorByEdgeId.get(edgeId);
      if (!currentDoorId || assignDoor(currentDoorId, visited)) {
        matchedDoorByEdgeId.set(edgeId, doorId);
        return true;
      }
    }
    return false;
  }

  for (const doorId of doorIds) {
    assignDoor(doorId);
  }

  const assignedEdgeByDoorId = new Map();
  for (const [edgeId, doorId] of matchedDoorByEdgeId.entries()) {
    const edge = edgeById.get(edgeId);
    if (edge) assignedEdgeByDoorId.set(doorId, edge);
  }
  return assignedEdgeByDoorId;
}

function placeRoomDoorNodes(view) {
  const nodeById = new Map((view.nodes || []).map((node) => [node.id, node]));
  const roomDoorNodes = (view.nodes || []).filter((node) => isRoomDoorNode(node));
  for (const node of roomDoorNodes) {
    const point = roomDoorPoint(node, nodeById, view.edges || []);
    if (!point) continue;
    const diameter = floorplanNodeDiameter(node);
    node.x = point.x;
    node.y = point.y;
    node.width = diameter;
    node.height = diameter;
    node.floorplanCircle = true;
    node.labelHidden = false;
    node.labelX = node.x;
    node.labelY = node.y + diameter * 1.25;
    node.hiddenInFloorplan = false;
  }
}

function roomCircleCandidates(roomLayout, count) {
  const cx = roomLayout.x + roomLayout.w / 2;
  const cy = roomLayout.y + roomLayout.h / 2;
  const rx = Math.max(0.26, roomLayout.w / 2 - 0.42);
  const ry = Math.max(0.26, roomLayout.h / 2 - 0.48);
  const points = [];
  if (count <= 0) return points;
  if (count === 1) return [{ x: cx, y: cy }];
  const ringCount = Math.max(1, Math.ceil(count / 6));
  let placed = 0;
  for (let ring = 0; ring < ringCount; ring += 1) {
    const remaining = count - placed;
    const take = ring === 0 ? Math.min(remaining, 6) : Math.min(remaining, 8 + ring * 4);
    const scale = ringCount === 1 ? 0.58 : 0.38 + (ring / Math.max(1, ringCount - 1)) * 0.46;
    for (let index = 0; index < take; index += 1) {
      const angle = -Math.PI / 2 + (index / take) * Math.PI * 2;
      points.push({
        x: cx + Math.cos(angle) * rx * scale,
        y: cy + Math.sin(angle) * ry * scale,
      });
    }
    placed += take;
  }
  return points;
}

function roomZoneCandidates(roomLayout, count, zone, doorways = []) {
  const cx = roomLayout.x + roomLayout.w / 2;
  const cy = roomLayout.y + roomLayout.h / 2;
  if (count <= 0) return [];
  if (zone === "agent") {
    if (doorways.length) {
      const doorway = doorways[0];
      const inwardX = doorway.orientation === "vertical"
        ? (doorway.x < cx ? 0.45 : -0.45)
        : 0;
      const inwardY = doorway.orientation === "horizontal"
        ? (doorway.y < cy ? 0.45 : -0.45)
        : 0;
      const baseX = doorway.x + inwardX;
      const baseY = doorway.y + inwardY;
      const points = [];
      for (let index = 0; index < count; index += 1) {
        points.push({
          x: baseX + index * 0.16,
          y: baseY + (index % 2 === 0 ? 0 : 0.12),
        });
      }
      return points;
    }
    const radius = Math.min(roomLayout.w, roomLayout.h) * 0.14;
    const points = [];
    for (let index = 0; index < count; index += 1) {
      const angle = Math.PI / 3 + (index / Math.max(1, count)) * (Math.PI / 3);
      points.push({
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
      });
    }
    return points;
  }
  if (zone === "door" && doorways.length) {
    const doorway = doorways[0];
    const base = { x: doorway.x, y: doorway.y };
    const radius = Math.min(roomLayout.w, roomLayout.h) * 0.18;
    const points = [];
    for (let index = 0; index < count; index += 1) {
      const angle = -Math.PI / 2 + (index / Math.max(1, count)) * Math.PI * 2;
      points.push({ x: base.x + Math.cos(angle) * radius, y: base.y + Math.sin(angle) * radius });
    }
    return points;
  }
  if (zone === "wall") {
    const points = [];
    const positions = [
      { x: roomLayout.x + roomLayout.w * 0.2, y: roomLayout.y + roomLayout.h * 0.18 },
      { x: roomLayout.x + roomLayout.w * 0.8, y: roomLayout.y + roomLayout.h * 0.18 },
      { x: roomLayout.x + roomLayout.w * 0.82, y: roomLayout.y + roomLayout.h * 0.5 },
      { x: roomLayout.x + roomLayout.w * 0.2, y: roomLayout.y + roomLayout.h * 0.5 },
      { x: roomLayout.x + roomLayout.w * 0.2, y: roomLayout.y + roomLayout.h * 0.82 },
      { x: roomLayout.x + roomLayout.w * 0.8, y: roomLayout.y + roomLayout.h * 0.82 },
    ];
    for (let i = 0; i < count; i += 1) {
      points.push(positions[i % positions.length]);
    }
    return points;
  }
  if (zone === "center") {
    const points = [];
    const radius = Math.min(roomLayout.w, roomLayout.h) * 0.16;
    for (let index = 0; index < count; index += 1) {
      const angle = -Math.PI / 2 + (index / Math.max(1, count)) * Math.PI * 2;
      points.push({ x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius });
    }
    return points;
  }
  return roomCircleCandidates(roomLayout, count);
}

function childOrbitCandidates(parentNode, count) {
  const radius = Math.max(0.18, (Number(parentNode.width) || 0.2) * 0.9);
  const points = [];
  for (let index = 0; index < count; index += 1) {
    const angle = -Math.PI / 2 + (index / Math.max(count, 1)) * Math.PI * 2;
    points.push({
      x: parentNode.x + Math.cos(angle) * radius,
      y: parentNode.y + Math.sin(angle) * radius,
    });
  }
  return points;
}

function shouldShowFloorplanLabel(node) {
  if (node.kind === "room") return true;
  if (node.kind === "agent" || nodeTypeOf(node) === "agent") return true;
  const semantic = semanticTypeOf(node);
  const majorSemantics = new Set([
    "sofa",
    "tv",
    "coffee_table",
    "air_conditioner",
    "trash_bin",
    "bed",
    "wardrobe",
    "desk",
    "counter",
    "sink",
    "fridge",
    "stove",
    "dishwasher",
    "microwave",
    "toilet",
    "washer",
    "shoe_rack",
    "seat",
    "chair",
    "plant",
  ]);
  return majorSemantics.has(semantic);
}

function layoutFloorplanRoomNodes(view) {
  const nodeById = new Map((view.nodes || []).map((node) => [node.id, node]));
  const childrenById = buildChildrenMap(view);
  const nodesByRoom = new Map();
  for (const node of view.nodes || []) {
    if (node.kind === "room") continue;
    const roomId = resolveRoomId(node, nodeById);
    node.room_id = roomId || node.room_id || "";
    if (!roomId) continue;
    if (!nodesByRoom.has(roomId)) nodesByRoom.set(roomId, []);
    nodesByRoom.get(roomId).push(node);
  }

  const roomDoorNodes = (view.nodes || []).filter((node) => isRoomDoorNode(node));

  for (const room of view.nodes || []) {
    if (room.kind !== "room" || !room.layout) continue;
    const roomNodes = nodesByRoom.get(room.id) || [];
    const topLevel = [];
    const childrenByParent = new Map();
    for (const node of roomNodes) {
      const parentId = String(node.meta?.parent || node.parent || "");
      if (!parentId || parentId === room.id) {
        topLevel.push(node);
      } else {
        if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
        childrenByParent.get(parentId).push(node);
      }
    }

    const controlNodes = [];
    const applianceNodes = [];
    const movableNodes = [];
    const agentNodes = [];
    const otherNodes = [];
    for (const node of topLevel) {
      if (isRoomDoorNode(node)) {
        continue;
      }
      const semanticClass = String(node.meta?.semantic_class || "");
      if (node.kind === "agent" || nodeTypeOf(node) === "agent") {
        agentNodes.push(node);
      } else if (semanticClass === "control") {
        controlNodes.push(node);
      } else if (semanticClass === "appliance") {
        applianceNodes.push(node);
      } else if (node.kind === "movable" || nodeTypeOf(node) === "movable_object") {
        movableNodes.push(node);
      } else {
        otherNodes.push(node);
      }
    }

    const groups = [
      { nodes: controlNodes, zone: "door" },
      { nodes: applianceNodes, zone: "wall" },
      { nodes: otherNodes, zone: "center" },
      { nodes: movableNodes, zone: "center" },
      { nodes: agentNodes, zone: "agent" },
    ];

    for (const group of groups) {
      const candidates = roomZoneCandidates(room.layout, group.nodes.length, group.zone, room.layout.doorways || []);
      group.nodes
        .sort((left, right) => String(left.id).localeCompare(String(right.id)))
        .forEach((node, index) => {
          const point = candidates[index] || {
            x: room.layout.x + room.layout.w / 2,
            y: room.layout.y + room.layout.h / 2,
          };
          const diameter = floorplanNodeDiameter(node);
          node.x = point.x;
          node.y = point.y;
          node.width = diameter;
          node.height = diameter;
          node.floorplanCircle = true;
          node.labelHidden = !shouldShowFloorplanLabel(node);
          node.labelX = node.x;
          node.labelY = node.y + diameter * 1.25;
          node.hiddenInFloorplan = false;

          const children = childrenByParent.get(String(node.id)) || [];
          const expand = state.expandedNodes.has(String(node.id));
          const childPoints = childOrbitCandidates(node, children.length);
          children
            .sort((left, right) => String(left.id).localeCompare(String(right.id)))
            .forEach((child, childIndex) => {
              if (!expand) {
                child.hiddenInFloorplan = true;
                child.labelHidden = true;
                return;
              }
              const childPoint = childPoints[childIndex] || { x: node.x, y: node.y };
              const childDiameter = floorplanNodeDiameter(child);
              child.x = childPoint.x;
              child.y = childPoint.y;
              child.width = childDiameter;
              child.height = childDiameter;
              child.floorplanCircle = true;
              child.labelHidden = !shouldShowFloorplanLabel(child);
              child.labelX = child.x;
              child.labelY = child.y + childDiameter * 1.15;
              child.hiddenInFloorplan = false;
            });
        });
    }
  }

  roomDoorNodes
    .sort((left, right) => String(left.id).localeCompare(String(right.id)))
    .forEach((node) => {
      const point = roomDoorPoint(node, nodeById) || { x: 0, y: 0 };
      const diameter = floorplanNodeDiameter(node);
      node.x = point.x;
      node.y = point.y;
      node.width = diameter;
      node.height = diameter;
      node.floorplanCircle = true;
      node.labelHidden = !shouldShowFloorplanLabel(node);
      node.labelX = node.x;
      node.labelY = node.y + diameter * 1.25;
      node.hiddenInFloorplan = false;
    });
}

function cloneFloorplanView(rawView) {
  const view = cloneView(rawView);
  view.layout_mode = "floorplan";
  view.floorplan_bounds = normalizeRectLayout(rawView?.floorplan_bounds);
  const nodeById = new Map((view.nodes || []).map((node) => [node.id, node]));
  for (const node of view.nodes || []) {
    const layout = normalizeRectLayout(node.layout);
    node.layout = layout;
    node.hiddenInFloorplan = false;
    node.floorplanCircle = false;
    if (node.kind === "room" && layout) {
      node.x = layout.x + layout.w / 2;
      node.y = layout.y + layout.h / 2;
      node.width = layout.w;
      node.height = layout.h;
      node.labelX = layout.x + layout.w / 2;
      node.labelY = layout.y + 0.42;
      node.labelAnchor = "middle";
    }
    if (node.kind !== "room") {
      node.room_id = resolveRoomId(node, nodeById);
    }
  }
  layoutFloorplanRoomNodes(view);
  return view;
}

function cloneView(view) {
  return {
    ...view,
    nodes: (view?.nodes || []).map((node) => ({ ...node, meta: cloneData(node.meta || {}) || {} })),
    edges: (view?.edges || []).map((edge) => ({ ...edge, meta: cloneData(edge.meta || {}) || {} })),
  };
}

function mapNodesById(view) {
  return new Map((view?.nodes || []).map((node) => [node.id, node]));
}

function samePlacementContext(nextNode, prevNode) {
  if (!nextNode || !prevNode) return false;
  const nextParent = String(nextNode.meta?.parent || "");
  const prevParent = String(prevNode.meta?.parent || "");
  return (
    String(nextNode.room_id || "") === String(prevNode.room_id || "") &&
    nextParent === prevParent
  );
}

function isAgentNode(node) {
  return node?.kind === "agent" || nodeTypeOf(node) === "agent";
}

function stableNodeIds(view, previousView) {
  const stable = new Set();
  if (!previousView) return stable;
  const prevById = mapNodesById(previousView);
  const unstable = new Set();
  const affectedRooms = new Set();
  const affectedParents = new Set();

  for (const node of view.nodes || []) {
    const prev = prevById.get(node.id);
    if (!prev) {
      unstable.add(node.id);
      affectedRooms.add(String(node.room_id || ""));
      affectedParents.add(String(node.meta?.parent || ""));
      continue;
    }
    const movedContext = !samePlacementContext(node, prev);
    const isAgent = node.kind === "agent" || nodeTypeOf(node) === "agent";
    if (movedContext || isAgent) {
      unstable.add(node.id);
      affectedRooms.add(String(node.room_id || ""));
      affectedRooms.add(String(prev.room_id || ""));
      affectedParents.add(String(node.meta?.parent || ""));
      affectedParents.add(String(prev.meta?.parent || ""));
    }
  }

  for (const node of view.nodes || []) {
    const prev = prevById.get(node.id);
    if (!prev) continue;
    const nodeParent = String(node.meta?.parent || "");
    if (
      unstable.has(node.id) ||
      affectedRooms.has(String(node.id || "")) ||
      affectedRooms.has(String(node.room_id || "")) ||
      affectedParents.has(String(node.id || "")) ||
      affectedParents.has(nodeParent)
    ) continue;
    if (node.kind === "room" || samePlacementContext(node, prev)) {
      stable.add(node.id);
    }
  }
  return stable;
}

function fixedStructureNodeIds(view, previousView) {
  const locked = new Set();
  if (!previousView) return locked;
  const prevById = mapNodesById(previousView);
  for (const node of view.nodes || []) {
    const prev = prevById.get(node.id);
    if (!prev) continue;
    if (isAgentNode(node) || isAgentNode(prev)) continue;
    if (node.kind === "room" && prev.kind === "room") {
      locked.add(node.id);
      continue;
    }
    if (samePlacementContext(node, prev)) {
      locked.add(node.id);
    }
  }
  return locked;
}

function stabilizeWithPreviousLayout(view, previousView, lockedIds = new Set()) {
  if (!previousView) return view;
  const prevById = mapNodesById(previousView);
  for (const node of view.nodes || []) {
    if (!lockedIds.has(node.id)) continue;
    const prev = prevById.get(node.id);
    if (!prev) continue;
    node.x = prev.x;
    node.y = prev.y;
  }
  return view;
}

function structureSignature(view) {
  const nodeSig = (view?.nodes || [])
    .map((node) => [
      node.id,
      node.kind,
      String(node.room_id || ""),
      String(node.meta?.parent || ""),
      String(node.meta?.node_type || ""),
    ].join("|"))
    .sort()
    .join("||");
  const edgeSig = (view?.edges || [])
    .map((edge) => [
      edge.kind,
      String(edge.source || ""),
      String(edge.target || ""),
    ].join("|"))
    .sort()
    .join("||");
  return `${view?.floor_id || "main"}::${nodeSig}::${edgeSig}`;
}

function nonAgentStructureSignature(view) {
  const agentIds = new Set((view?.nodes || []).filter((node) => isAgentNode(node)).map((node) => node.id));
  const nodeSig = (view?.nodes || [])
    .filter((node) => !agentIds.has(node.id))
    .map((node) => [
      node.id,
      node.kind,
      String(node.room_id || ""),
      String(node.meta?.parent || ""),
      String(node.meta?.node_type || ""),
    ].join("|"))
    .sort()
    .join("||");
  const edgeSig = (view?.edges || [])
    .filter((edge) => !agentIds.has(edge.source) && !agentIds.has(edge.target))
    .map((edge) => [
      edge.kind,
      String(edge.source || ""),
      String(edge.target || ""),
    ].join("|"))
    .sort()
    .join("||");
  return `${view?.floor_id || "main"}::${nodeSig}::${edgeSig}`;
}

function mergeLayoutPositions(previousView, rawView) {
  const merged = cloneView(rawView);
  const prevById = mapNodesById(previousView);
  for (const node of merged.nodes || []) {
    const prev = prevById.get(node.id);
    if (!prev) continue;
    node.x = prev.x;
    node.y = prev.y;
    if (typeof prev.labelX === "number") node.labelX = prev.labelX;
    if (typeof prev.labelY === "number") node.labelY = prev.labelY;
  }
  merged.__layoutSignature = structureSignature(rawView);
  return merged;
}

function countNodeOverlaps(view) {
  const nodes = (view?.nodes || []).filter((node) => node.kind !== "room");
  let overlaps = 0;
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      if (rectsOverlap(nodeCombinedBox(nodes[i]), nodeCombinedBox(nodes[j]), 2)) {
        overlaps += 1;
      }
    }
  }
  return overlaps;
}

function rectsOverlap(a, b, padding = 14) {
  return !(
    a.x + a.width / 2 + padding < b.x - b.width / 2 ||
    a.x - a.width / 2 - padding > b.x + b.width / 2 ||
    a.y + a.height / 2 + padding < b.y - b.height / 2 ||
    a.y - a.height / 2 - padding > b.y + b.height / 2
  );
}

function nodeVisualSize(node) {
  if (node.floorplanCircle) {
    const size = Number(node.width) || floorplanNodeDiameter(node);
    return { width: size, height: size };
  }
  if (node.layout) {
    const layout = normalizeRectLayout(node.layout);
    if (layout) {
      return { width: layout.w, height: layout.h };
    }
  }
  const nodeType = nodeTypeOf(node);
  if (node.kind === "room") return { width: 68, height: 68 };
  if (node.kind === "agent" || nodeType === "agent") return { width: 22, height: 22 };
  if (nodeType === "movable_object" || node.kind === "movable") return { width: 24, height: 24 };
  return { width: 32, height: 32 };
}

function roomCollisionSize(node) {
  const size = nodeVisualSize(node);
  if (node.kind !== "room") return size;
  return { width: size.width + 64, height: size.height + 64 };
}

function placeNode(node, candidates, placed, fallback) {
  let best = fallback;
  let bestPenalty = Number.POSITIVE_INFINITY;
  for (const candidate of candidates) {
    const probe = {
      x: candidate.x,
      y: candidate.y,
      width: node.width,
      height: node.height,
    };
    let penalty = 0;
    for (const other of placed) {
      if (rectsOverlap(probe, other, 12)) penalty += 1000;
      const dx = probe.x - other.x;
      const dy = probe.y - other.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 1) penalty += 500;
    }
    penalty += Math.hypot(candidate.x - fallback.x, candidate.y - fallback.y) * 0.04;
    if (penalty < bestPenalty) {
      bestPenalty = penalty;
      best = candidate;
      if (penalty === 0) break;
    }
  }
  node.x = best.x;
  node.y = best.y;
  placed.push({ x: node.x, y: node.y, width: node.width, height: node.height });
}

function roomClusterCandidates(roomNode, clusterIndex, slotCount = 14) {
  const radiusX = roomNode.width / 2 + LAYOUT_TUNING.roomClusters.candidateRadiusX;
  const radiusY = roomNode.height / 2 + LAYOUT_TUNING.roomClusters.candidateRadiusY;
  const phase = (clusterIndex % slotCount) * ((2 * Math.PI) / slotCount);
  const candidates = [];
  for (let ring = 0; ring < LAYOUT_TUNING.roomClusters.candidateRings; ring += 1) {
    const scale = 1 + ring * LAYOUT_TUNING.roomClusters.candidateRingScale;
    for (let step = 0; step < slotCount; step += 1) {
      const angle = phase + step * ((2 * Math.PI) / slotCount);
      candidates.push({
        x: roomNode.x + Math.cos(angle) * radiusX * scale,
        y: roomNode.y + Math.sin(angle) * radiusY * scale,
      });
    }
  }
  return candidates;
}

function sortNodesForLayout(nodes) {
  return [...nodes].sort((a, b) => {
    const rank = (node) => {
      if (node.kind === "fixture") return 0;
      if (node.kind === "agent") return 1;
      return 2;
    };
    return rank(a) - rank(b) || String(a.label).localeCompare(String(b.label), "zh-CN");
  });
}

function objectClusterOffset(
  index,
  count = 1,
  angle = Math.PI / 2,
  gapX = LAYOUT_TUNING.childGrid.gapX,
  gapY = LAYOUT_TUNING.childGrid.gapY
) {
  const columns = Math.max(1, Math.min(3, Math.ceil(Math.sqrt(Math.max(count, 1)))));
  const column = index % columns;
  const row = Math.floor(index / columns);
  const columnOffset = column - (columns - 1) / 2;
  const rowOffset = row;
  const ux = Math.cos(angle);
  const uy = Math.sin(angle);
  const px = -uy;
  const py = ux;
  const baseOutward = 26;
  const outward = baseOutward + rowOffset * Math.max(18, gapY * 0.55);
  const lateral = columnOffset * Math.max(18, gapX * 0.52);
  return {
    x: ux * outward + px * lateral,
    y: uy * outward + py * lateral,
  };
}

function clusterDimensions(parentNode, children) {
  const parentSize = nodeVisualSize(parentNode);
  const columns = Math.max(1, Math.min(3, Math.ceil(Math.sqrt(Math.max(children.length, 1)))));
  const rows = Math.max(1, Math.ceil(children.length / columns));
  const childAreaWidth = children.length ? columns * 34 + 18 : 0;
  const childAreaHeight = children.length ? rows * 30 + 20 : 0;
  return {
    width: Math.max(parentSize.width + 18, childAreaWidth),
    height: parentSize.height + childAreaHeight + 18,
    columns,
  };
}

function clusterRadius(cluster) {
  return Math.max(cluster.width, cluster.height) / 2 + 12;
}

function estimateRoomDemandRadius(roomNode, nodeById, childrenByParent) {
  const baseRoomRadius = Math.max(roomCollisionSize(roomNode).width, roomCollisionSize(roomNode).height) / 2;
  const directChildren = (childrenByParent.get(roomNode.id) || [])
    .map((childId) => nodeById.get(childId))
    .filter(Boolean);
  if (!directChildren.length) {
    return baseRoomRadius + LAYOUT_TUNING.roomClusters.shellInner + 8;
  }

  let totalClusterArea = 0;
  let maxClusterRadius = 0;
  for (const parentNode of directChildren) {
    const descendants = ((childrenByParent.get(parentNode.id) || [])
      .map((childId) => nodeById.get(childId))
      .filter(Boolean));
    const bounds = clusterDimensions(parentNode, descendants);
    totalClusterArea += bounds.width * bounds.height;
    maxClusterRadius = Math.max(maxClusterRadius, Math.max(bounds.width, bounds.height) / 2);
  }

  const areaRadius = Math.sqrt(totalClusterArea / Math.PI) * 0.56;
  const shellRadius = LAYOUT_TUNING.roomClusters.shellInner + LAYOUT_TUNING.roomClusters.anchorBaseOffset;
  return baseRoomRadius + Math.max(shellRadius + maxClusterRadius * 0.3, areaRadius + 26);
}

function relaxRoomPositions(rooms, roomNeighbors, roomDemandRadius) {
  if (rooms.length <= 1) return;
  const roomById = new Map(rooms.map((room) => [room.id, room]));
  for (const room of rooms) {
    room.vx = 0;
    room.vy = 0;
  }

  const neighborPairs = [];
  const seenPairs = new Set();
  for (const room of rooms) {
    for (const neighbor of roomNeighbors.get(room.id) || []) {
      const key = [room.id, neighbor.id].sort().join("::");
      if (seenPairs.has(key)) continue;
      seenPairs.add(key);
      neighborPairs.push([room, roomById.get(neighbor.id) || neighbor]);
    }
  }

  for (let iter = 0; iter < LAYOUT_TUNING.roomLayout.iterations; iter += 1) {
    for (const room of rooms) {
      let fx = -room.x * LAYOUT_TUNING.roomLayout.globalCenterPull;
      let fy = -room.y * LAYOUT_TUNING.roomLayout.globalCenterPull;

      for (const other of rooms) {
        if (other.id === room.id) continue;
        const dx = room.x - other.x;
        const dy = room.y - other.y;
        const dist = Math.hypot(dx, dy) || 1;
        const minDist =
          roomDemandRadius.get(room.id) +
          roomDemandRadius.get(other.id) +
          LAYOUT_TUNING.roomLayout.roomRepulsionPadding;
        if (dist < minDist) {
          const push = (minDist - dist) * LAYOUT_TUNING.roomLayout.roomRepulsionStrength;
          fx += (dx / dist) * push;
          fy += (dy / dist) * push;
        }
      }

      room.vx = (room.vx + fx) * LAYOUT_TUNING.roomLayout.damping;
      room.vy = (room.vy + fy) * LAYOUT_TUNING.roomLayout.damping;
    }

    for (const [left, right] of neighborPairs) {
      const dx = right.x - left.x;
      const dy = right.y - left.y;
      const dist = Math.hypot(dx, dy) || 1;
      const target =
        roomDemandRadius.get(left.id) +
        roomDemandRadius.get(right.id) +
        LAYOUT_TUNING.roomLayout.neighborGap;
      const delta = dist - target;
      const pull = delta * LAYOUT_TUNING.roomLayout.neighborSpring;
      const ux = dx / dist;
      const uy = dy / dist;
      left.vx += ux * pull;
      left.vy += uy * pull;
      right.vx -= ux * pull;
      right.vy -= uy * pull;
    }

    for (const room of rooms) {
      room.x += room.vx;
      room.y += room.vy;
    }
  }
}

function clampClusterToShell(cluster, roomNode, innerRadius, outerRadius) {
  const dx = cluster.x - roomNode.x;
  const dy = cluster.y - roomNode.y;
  const dist = Math.hypot(dx, dy) || 1;
  if (dist < innerRadius) {
    const scale = innerRadius / dist;
    cluster.x = roomNode.x + dx * scale;
    cluster.y = roomNode.y + dy * scale;
  } else if (dist > outerRadius) {
    const scale = outerRadius / dist;
    cluster.x = roomNode.x + dx * scale;
    cluster.y = roomNode.y + dy * scale;
  }
}

function circleRadiusForNode(node) {
  const nodeType = nodeTypeOf(node);
  if (node.kind === "room") return 34;
  if (node.kind === "agent" || nodeType === "agent") return 14;
  if (nodeType === "movable_object" || node.kind === "movable") return 16;
  return 18;
}

function minimumNodeSeparation(a, b) {
  return circleRadiusForNode(a) + circleRadiusForNode(b) + 8;
}

function roomExclusionRadius(roomNode, node, padding = 0) {
  const roomRadius = Math.max(roomCollisionSize(roomNode).width, roomCollisionSize(roomNode).height) / 2;
  return roomRadius + circleRadiusForNode(node) + padding;
}

function overlapArea(a, b, padding = 0) {
  const overlapX = Math.min(a.x + a.width / 2 + padding, b.x + b.width / 2 + padding)
    - Math.max(a.x - a.width / 2 - padding, b.x - b.width / 2 - padding);
  const overlapY = Math.min(a.y + a.height / 2 + padding, b.y + b.height / 2 + padding)
    - Math.max(a.y - a.height / 2 - padding, b.y - b.height / 2 - padding);
  if (overlapX <= 0 || overlapY <= 0) return 0;
  return overlapX * overlapY;
}

function placeMovingAgentInOpenSlot(agentNode, view, previousView = null) {
  const nodeById = new Map((view.nodes || []).map((node) => [node.id, node]));
  const roomNode = nodeById.get(agentNode.room_id);
  if (!roomNode || roomNode.kind !== "room") return;
  const prevById = mapNodesById(previousView);
  const prevAgent = prevById.get(agentNode.id);
  const others = (view.nodes || []).filter((node) => node.id !== agentNode.id);
  const neighbors = [];
  for (const edge of view.edges || []) {
    if (edge.kind !== "neighbor") continue;
    if (edge.source === roomNode.id && nodeById.get(edge.target)?.kind === "room") neighbors.push(nodeById.get(edge.target));
    if (edge.target === roomNode.id && nodeById.get(edge.source)?.kind === "room") neighbors.push(nodeById.get(edge.source));
  }

  const baseRadius = roomExclusionRadius(roomNode, agentNode, 18);
  const preferredAngle = prevAgent
    ? Math.atan2(prevAgent.y - roomNode.y, prevAgent.x - roomNode.x)
    : -Math.PI / 3;
  const candidateRings = [baseRadius + 12, baseRadius + 42, baseRadius + 74];
  let best = { x: roomNode.x + Math.cos(preferredAngle) * candidateRings[0], y: roomNode.y + Math.sin(preferredAngle) * candidateRings[0] };
  let bestPenalty = Number.POSITIVE_INFINITY;

  for (const radius of candidateRings) {
    for (let step = 0; step < 18; step += 1) {
      const angle = preferredAngle + (step / 18) * Math.PI * 2;
      agentNode.x = roomNode.x + Math.cos(angle) * radius;
      agentNode.y = roomNode.y + Math.sin(angle) * radius;
      assignLabelBelow(agentNode);
      const candidateBox = nodeCombinedBox(agentNode);
      let penalty = 0;

      for (const other of others) {
        const otherBox = nodeCombinedBox(other);
        const area = overlapArea(candidateBox, otherBox, 4);
        if (area > 0) penalty += 100000 + area * 10;
      }

      for (const other of (view.nodes || []).filter((node) => node.kind === "room" && node.id !== roomNode.id)) {
        const dx = agentNode.x - other.x;
        const dy = agentNode.y - other.y;
        const dist = Math.hypot(dx, dy) || 1;
        const minDist = roomExclusionRadius(other, agentNode, LAYOUT_TUNING.roomClusters.otherRoomNodePadding);
        if (dist < minDist) penalty += 100000 + (minDist - dist) * 1000;
      }

      for (const neighbor of neighbors) {
        const corridor = pointSegmentDistance(agentNode.x, agentNode.y, roomNode.x, roomNode.y, neighbor.x, neighbor.y);
        const minCorridor = circleRadiusForNode(agentNode) + 16;
        if (corridor.distance < minCorridor) penalty += 3000 + (minCorridor - corridor.distance) * 200;
      }

      if (prevAgent) {
        penalty += Math.hypot(agentNode.x - prevAgent.x, agentNode.y - prevAgent.y) * 0.15;
      }

      penalty += Math.hypot(agentNode.x - roomNode.x, agentNode.y - roomNode.y) * 0.02;
      if (penalty < bestPenalty) {
        bestPenalty = penalty;
        best = { x: agentNode.x, y: agentNode.y };
        if (penalty === 0) break;
      }
    }
  }

  agentNode.x = best.x;
  agentNode.y = best.y;
  assignLabelBelow(agentNode);
}

function incrementalRelayoutView(rawView, previousView) {
  const view = mergeLayoutPositions(previousView, rawView);
  const prevById = mapNodesById(previousView);
  const changedIds = new Set();
  let hasNonAgentStructuralChange = false;
  for (const node of view.nodes || []) {
    const prev = prevById.get(node.id);
    if (!prev || !samePlacementContext(node, prev)) {
      changedIds.add(node.id);
      if (!isAgentNode(node)) hasNonAgentStructuralChange = true;
    }
  }

  if (hasNonAgentStructuralChange) {
    return layoutViewWithPhysics(rawView, previousView);
  }

  for (const node of view.nodes || []) {
    if (!changedIds.has(node.id)) continue;
    if (isAgentNode(node)) {
      placeMovingAgentInOpenSlot(node, view, previousView);
    }
  }

  assignLabelsBelow(view);
  const lockedIds = new Set((view.nodes || []).filter((node) => !changedIds.has(node.id)).map((node) => node.id));
  resolveNodeOverlaps(view, lockedIds);
  resolveHardNodeCollisions(view, lockedIds);
  assignLabelsBelow(view);
  resolveLabelOverlaps(view);
  return view;
}

function parentTetherBounds(parentNode, node) {
  const base = circleRadiusForNode(parentNode) + circleRadiusForNode(node);
  return {
    min: base + 6,
    max: base + Math.max(18, LAYOUT_TUNING.childGrid.gapX * 0.38),
  };
}

function nodeCombinedBox(node) {
  const nodeRadius = circleRadiusForNode(node);
  const nodeWidth = nodeRadius * 2;
  const nodeHeight = nodeRadius * 2;
  if (node.kind === "room" || node.labelHidden) {
    return { x: node.x, y: node.y, width: nodeWidth, height: nodeHeight };
  }

  const metrics = labelMetrics(node);
  const labelOffset = Math.max(24, nodeLabelOffset(node));
  const top = node.y - nodeHeight / 2;
  const bottom = node.y + labelOffset + metrics.height / 2;
  return {
    x: node.x,
    y: (top + bottom) / 2,
    width: Math.max(nodeWidth, metrics.width),
    height: bottom - top,
  };
}

function resolveNodeOverlaps(view, lockedIds = new Set()) {
  const nodeById = new Map((view.nodes || []).map((node) => [node.id, node]));
  const rooms = (view.nodes || []).filter((node) => node.kind === "room");
  const roomNeighbors = new Map(rooms.map((room) => [room.id, []]));
  const controlSegments = [];
  for (const edge of view.edges || []) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (edge.kind === "neighbor") {
      if (!source || !target || source.kind !== "room" || target.kind !== "room") continue;
      roomNeighbors.get(source.id)?.push(target);
      roomNeighbors.get(target.id)?.push(source);
      continue;
    }
    if (edge.kind === "controls" && source && target) {
      controlSegments.push({ source, target });
    }
  }

  const movableNodes = (view.nodes || []).filter((node) => node.kind !== "room");
  for (let iter = 0; iter < 90; iter += 1) {
    let moved = false;
    for (let i = 0; i < movableNodes.length; i += 1) {
      for (let j = i + 1; j < movableNodes.length; j += 1) {
        const left = movableNodes[i];
        const right = movableNodes[j];
        const leftBox = nodeCombinedBox(left);
        const rightBox = nodeCombinedBox(right);
        if (!rectsOverlap(leftBox, rightBox, 6)) continue;
        const dx = right.x - left.x;
        const dy = right.y - left.y;
        const dist = Math.hypot(dx, dy) || 1;
        const overlapX = (leftBox.width + rightBox.width) / 2 + 6 - Math.abs(dx);
        const overlapY = (leftBox.height + rightBox.height) / 2 + 6 - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;
        const leftLocked = lockedIds.has(left.id);
        const rightLocked = lockedIds.has(right.id);
        if (leftLocked && rightLocked) continue;
        if (overlapX < overlapY) {
          const pushX = (leftLocked || rightLocked) ? overlapX : overlapX / 2;
          const sign = dx >= 0 ? 1 : -1;
          if (!rightLocked) right.x += sign * pushX;
          if (!leftLocked) left.x -= sign * pushX;
        } else {
          const pushY = (leftLocked || rightLocked) ? overlapY : overlapY / 2;
          const sign = dy >= 0 ? 1 : -1;
          if (!rightLocked) right.y += sign * pushY;
          if (!leftLocked) left.y -= sign * pushY;
        }
        moved = true;
      }
    }

    for (const node of movableNodes) {
      if (lockedIds.has(node.id)) continue;
      const room = nodeById.get(node.room_id);
      const parentId = String(node.meta?.parent || "");
      const parentNode = parentId ? nodeById.get(parentId) : null;
      if (room?.kind === "room") {
        const roomExclusion = roomExclusionRadius(
          room,
          node,
          LAYOUT_TUNING.roomClusters.ownRoomNodePadding
        );
        const maxDist = 214;
        const dx = node.x - room.x;
        const dy = node.y - room.y;
        const dist = Math.hypot(dx, dy) || 1;
        if (dist < roomExclusion) {
          const push = (roomExclusion - dist) * LAYOUT_TUNING.roomClusters.roomNodeRepulsionStrength;
          node.x += (dx / dist) * push;
          node.y += (dy / dist) * push;
          moved = true;
        } else if (dist > maxDist) {
          const scale = maxDist / dist;
          node.x = room.x + dx * scale;
          node.y = room.y + dy * scale;
          moved = true;
        }

        for (const otherRoom of rooms) {
          if (otherRoom.id === room.id) continue;
          const otherDx = node.x - otherRoom.x;
          const otherDy = node.y - otherRoom.y;
          const otherDist = Math.hypot(otherDx, otherDy) || 1;
          const minOtherDist = roomExclusionRadius(
            otherRoom,
            node,
            LAYOUT_TUNING.roomClusters.otherRoomNodePadding
          );
          if (otherDist < minOtherDist) {
            const push = (minOtherDist - otherDist) * LAYOUT_TUNING.roomClusters.roomNodeRepulsionStrength;
            node.x += (otherDx / otherDist) * push;
            node.y += (otherDy / otherDist) * push;
            moved = true;
          }
        }

        for (const neighbor of roomNeighbors.get(room.id) || []) {
          const corridor = pointSegmentDistance(node.x, node.y, room.x, room.y, neighbor.x, neighbor.y);
          const minCorridor = circleRadiusForNode(node) + 14;
          if (corridor.distance < minCorridor) {
            const cx = node.x - corridor.closestX;
            const cy = node.y - corridor.closestY;
            const cdist = Math.hypot(cx, cy) || 1;
            const push = minCorridor - corridor.distance;
            node.x += (cx / cdist) * push;
            node.y += (cy / cdist) * push;
            moved = true;
          }
        }
      }

      if (parentNode && parentNode.kind !== "room") {
        const dx = node.x - parentNode.x;
        const dy = node.y - parentNode.y;
        const dist = Math.hypot(dx, dy) || 1;
        const bounds = parentTetherBounds(parentNode, node);
        if (dist > bounds.max) {
          const pull = (dist - bounds.max) * 0.9;
          node.x -= (dx / dist) * pull;
          node.y -= (dy / dist) * pull;
          moved = true;
        } else if (dist < bounds.min) {
          const push = (bounds.min - dist) * 0.6;
          node.x += (dx / dist) * push;
          node.y += (dy / dist) * push;
          moved = true;
        }
      }

      for (const segment of controlSegments) {
        if (segment.source.id === node.id || segment.target.id === node.id) continue;
        const corridor = pointSegmentDistance(
          node.x,
          node.y,
          segment.source.x,
          segment.source.y,
          segment.target.x,
          segment.target.y
        );
        const minCorridor = circleRadiusForNode(node) + LAYOUT_TUNING.roomClusters.controlCorridorPadding;
        if (corridor.distance < minCorridor) {
          const dx = node.x - corridor.closestX;
          const dy = node.y - corridor.closestY;
          const dist = Math.hypot(dx, dy) || 1;
          const push = (minCorridor - corridor.distance) * LAYOUT_TUNING.roomClusters.controlCorridorRepulsionStrength;
          node.x += (dx / dist) * push;
          node.y += (dy / dist) * push;
          moved = true;
        }
      }
    }
    if (!moved) break;
  }
}

function resolveHardNodeCollisions(view, lockedIds = new Set()) {
  const nodeById = new Map((view.nodes || []).map((node) => [node.id, node]));
  const rooms = (view.nodes || []).filter((node) => node.kind === "room");
  const nonRooms = (view.nodes || []).filter((node) => node.kind !== "room");

  for (let iter = 0; iter < 140; iter += 1) {
    let moved = false;

    for (let i = 0; i < nonRooms.length; i += 1) {
      for (let j = i + 1; j < nonRooms.length; j += 1) {
        const left = nonRooms[i];
        const right = nonRooms[j];
        const leftBox = nodeCombinedBox(left);
        const rightBox = nodeCombinedBox(right);
        if (!rectsOverlap(leftBox, rightBox, 4)) continue;
        const dx = right.x - left.x;
        const dy = right.y - left.y;
        const overlapX = (leftBox.width + rightBox.width) / 2 + 4 - Math.abs(dx);
        const overlapY = (leftBox.height + rightBox.height) / 2 + 4 - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;
        const leftLocked = lockedIds.has(left.id);
        const rightLocked = lockedIds.has(right.id);
        if (leftLocked && rightLocked) continue;
        if (overlapX < overlapY) {
          const pushX = (leftLocked || rightLocked) ? overlapX : overlapX / 2;
          const sign = dx >= 0 ? 1 : -1;
          if (!rightLocked) right.x += sign * pushX;
          if (!leftLocked) left.x -= sign * pushX;
        } else {
          const pushY = (leftLocked || rightLocked) ? overlapY : overlapY / 2;
          const sign = dy >= 0 ? 1 : -1;
          if (!rightLocked) right.y += sign * pushY;
          if (!leftLocked) left.y -= sign * pushY;
        }
        moved = true;
      }
    }

    for (const node of nonRooms) {
      if (lockedIds.has(node.id)) continue;
      const room = nodeById.get(node.room_id);
      if (room?.kind === "room") {
        const dx = node.x - room.x;
        const dy = node.y - room.y;
        const dist = Math.hypot(dx, dy) || 1;
        const minDist = roomExclusionRadius(room, node, LAYOUT_TUNING.roomClusters.ownRoomNodePadding);
        if (dist < minDist) {
          const push = minDist - dist;
          node.x += (dx / dist) * push;
          node.y += (dy / dist) * push;
          moved = true;
        }
      }

      for (const otherRoom of rooms) {
        if (otherRoom.id === node.room_id) continue;
        const dx = node.x - otherRoom.x;
        const dy = node.y - otherRoom.y;
        const dist = Math.hypot(dx, dy) || 1;
        const minDist = roomExclusionRadius(otherRoom, node, LAYOUT_TUNING.roomClusters.otherRoomNodePadding);
        if (dist < minDist) {
          const push = minDist - dist;
          node.x += (dx / dist) * push;
          node.y += (dy / dist) * push;
          moved = true;
        }
      }
    }

    if (!moved) break;
  }
}

function resolveMovableObstacleConflicts(view, lockedIds = new Set()) {
  const nodeById = new Map((view.nodes || []).map((node) => [node.id, node]));
  const movers = (view.nodes || []).filter((node) => !lockedIds.has(node.id) && (node.kind === "movable" || node.kind === "agent"));
  const obstacles = (view.nodes || []).filter((node) => node.kind !== "room");
  for (let iter = 0; iter < 180; iter += 1) {
    let moved = false;
    for (const mover of movers) {
      const moverBox = nodeCombinedBox(mover);
      for (const obstacle of obstacles) {
        if (obstacle.id === mover.id) continue;
        const obstacleBox = nodeCombinedBox(obstacle);
        if (!rectsOverlap(moverBox, obstacleBox, 6)) continue;
        const dx = mover.x - obstacle.x;
        const dy = mover.y - obstacle.y;
        const dist = Math.hypot(dx, dy) || 1;
        const overlapX = (moverBox.width + obstacleBox.width) / 2 + 6 - Math.abs(mover.x - obstacle.x);
        const overlapY = (moverBox.height + obstacleBox.height) / 2 + 6 - Math.abs(mover.y - obstacle.y);
        if (overlapX <= 0 || overlapY <= 0) continue;
        if (overlapX < overlapY) {
          const sign = dx >= 0 ? 1 : -1;
          mover.x += sign * Math.max(overlapX, 6);
        } else {
          const sign = dy >= 0 ? 1 : -1;
          mover.y += sign * Math.max(overlapY, 6);
        }
        moved = true;
      }

      const room = nodeById.get(mover.room_id);
      if (room?.kind === "room") {
        const dx = mover.x - room.x;
        const dy = mover.y - room.y;
        const dist = Math.hypot(dx, dy) || 1;
        const minDist = roomExclusionRadius(room, mover, LAYOUT_TUNING.roomClusters.ownRoomNodePadding);
        const maxDist = Math.max(236, LAYOUT_TUNING.roomClusters.shellOuter + 34);
        if (dist < minDist) {
          const push = minDist - dist;
          mover.x += (dx / dist) * push;
          mover.y += (dy / dist) * push;
          moved = true;
        } else if (dist > maxDist) {
          mover.x = room.x + (dx / dist) * maxDist;
          mover.y = room.y + (dy / dist) * maxDist;
          moved = true;
        }
      }
    }
    if (!moved) break;
  }
}

function normalizeAngle(angle) {
  let next = angle;
  while (next <= -Math.PI) next += Math.PI * 2;
  while (next > Math.PI) next -= Math.PI * 2;
  return next;
}

function angularDistance(a, b) {
  return Math.abs(normalizeAngle(a - b));
}

function chooseAnchorAngle(roomNode, roomNeighbors, clusterIndex, clusterCount) {
  const forbidden = roomNeighbors.map((neighbor) => Math.atan2(neighbor.y - roomNode.y, neighbor.x - roomNode.x));
  const preferred = (clusterIndex / Math.max(1, clusterCount)) * Math.PI * 2 - Math.PI;
  let best = preferred;
  let bestScore = -Infinity;
  const samples = Math.max(16, clusterCount * 4);
  for (let i = 0; i < samples; i += 1) {
    const angle = -Math.PI + (i / samples) * Math.PI * 2;
    let clearance = Math.PI;
    for (const blocked of forbidden) {
      clearance = Math.min(clearance, angularDistance(angle, blocked));
    }
    const preference = angularDistance(angle, preferred);
    const score = clearance * 4 - preference;
    if (score > bestScore) {
      bestScore = score;
      best = angle;
    }
  }
  return best;
}

function pointSegmentDistance(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const denom = dx * dx + dy * dy || 1;
  const t = clamp(((px - x1) * dx + (py - y1) * dy) / denom, 0, 1);
  const closestX = x1 + dx * t;
  const closestY = y1 + dy * t;
  const distX = px - closestX;
  const distY = py - closestY;
  return {
    distance: Math.hypot(distX, distY),
    closestX,
    closestY,
  };
}

function clusterKeyForNodeId(nodeId, childrenByParent) {
  const parentId = String(nodeId || "");
  for (const [clusterParentId, childIds] of childrenByParent.entries()) {
    if (clusterParentId === parentId) return clusterParentId;
    if (childIds.includes(parentId)) return clusterParentId;
  }
  return parentId;
}

function labelFontSize(node) {
  const nodeType = nodeTypeOf(node);
  if (node.kind === "room") return 12;
  if (node.kind === "agent" || nodeType === "agent") return 11;
  if (nodeType === "movable_object" || node.kind === "movable") return 11;
  if (node.kind === "fixture") return 10;
  return 11;
}

function labelMetrics(node) {
  const fontSize = labelFontSize(node);
  const text = String(node.label || "");
  const width = Math.max(30, text.length * fontSize * 0.62);
  const height = fontSize + 6;
  return { fontSize, width, height };
}

function nodeLabelOffset(node) {
  const nodeType = nodeTypeOf(node);
  if (node.kind === "room") return 0;
  if (node.kind === "agent" || nodeType === "agent") return 28;
  if (nodeType === "movable_object" || node.kind === "movable") return 26;
  return 24;
}

function assignLabelBelow(node) {
  if (node.kind === "room") {
    node.labelX = node.x;
    node.labelY = node.y;
    node.labelAnchor = "middle";
    node.labelHidden = false;
    return;
  }
  node.labelX = node.x;
  node.labelY = node.y + nodeLabelOffset(node);
  node.labelAnchor = "middle";
  node.labelHidden = false;
}

function assignLabelsBelow(view) {
  for (const node of view.nodes || []) {
    assignLabelBelow(node);
  }
}

function labelBox(node) {
  const metrics = labelMetrics(node);
  return {
    x: Number(node.labelX ?? node.x),
    y: Number(node.labelY ?? node.y),
    width: metrics.width,
    height: metrics.height,
  };
}

function nodeBox(node) {
  const r = circleRadiusForNode(node);
  return { x: node.x, y: node.y, width: r * 2, height: r * 2 };
}

function resolveLabelOverlaps(view) {
  assignLabelsBelow(view);
}

function placeLabel(node, placedLabels, allNodeBoxes) {
  // Back-compat shim: we now enforce labels below nodes.
  assignLabelBelow(node);
}

function normalizeRoomPositions(roomPositions) {
  const ids = Object.keys(roomPositions);
  if (!ids.length) return roomPositions;
  const xs = ids.map((id) => roomPositions[id].x);
  const ys = ids.map((id) => roomPositions[id].y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(1, maxX - minX);
  const spanY = Math.max(1, maxY - minY);
  const targetWidth = 680;
  const targetHeight = 500;
  const scale = Math.min(targetWidth / spanX, targetHeight / spanY);
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const normalized = {};
  for (const id of ids) {
    normalized[id] = {
      x: (roomPositions[id].x - centerX) * scale,
      y: (roomPositions[id].y - centerY) * scale,
    };
  }
  return normalized;
}

function computeRoomLayoutWithDagre(view) {
  const rooms = (view?.nodes || []).filter((node) => node.kind === "room");
  if (!rooms.length || typeof dagre === "undefined") {
    return new Map(rooms.map((room) => [room.id, { x: room.x, y: room.y }]));
  }
  const graph = new dagre.graphlib.Graph({ multigraph: false, compound: false });
  graph.setGraph({
    rankdir: "LR",
    ranksep: 120,
    nodesep: 80,
    edgesep: 40,
    marginx: 20,
    marginy: 20,
  });
  graph.setDefaultEdgeLabel(() => ({}));

  for (const room of rooms) {
    const diameter = Math.max(room.width || 120, room.height || 46, 90);
    graph.setNode(room.id, { width: diameter, height: diameter });
  }

  const added = new Set();
  for (const edge of view?.edges || []) {
    if (edge.kind !== "neighbor") continue;
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;
    const key = [edge.source, edge.target].sort().join("::");
    if (added.has(key)) continue;
    added.add(key);
    graph.setEdge(edge.source, edge.target);
  }

  dagre.layout(graph);
  const rawPositions = {};
  for (const room of rooms) {
    const layoutNode = graph.node(room.id);
    rawPositions[room.id] = layoutNode ? { x: layoutNode.x, y: layoutNode.y } : { x: room.x, y: room.y };
  }
  const normalized = normalizeRoomPositions(rawPositions);
  return new Map(Object.entries(normalized));
}

function relayoutView(rawView) {
  const view = cloneView(rawView);
  const nodeById = new Map(view.nodes.map((node) => [node.id, node]));
  const rooms = view.nodes.filter((node) => node.kind === "room");
  const roomPositions = computeRoomLayoutWithDagre(view);
  for (const room of rooms) {
    const pos = roomPositions.get(room.id);
    if (pos) {
      room.x = pos.x;
      room.y = pos.y;
    }
  }
  const placed = rooms.map((node) => ({
    x: node.x,
    y: node.y,
    width: roomCollisionSize(node).width,
    height: roomCollisionSize(node).height,
    nodeId: node.id,
  }));
  const childrenByParent = new Map();

  for (const node of view.nodes) {
    const parentId = String(node.meta?.parent || node.room_id || "");
    if (!parentId || !nodeById.has(parentId)) continue;
    if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
    childrenByParent.get(parentId).push(node.id);
  }

  function sortNodes(nodes) {
    return [...nodes].sort((a, b) => {
      const rank = (node) => {
        if (node.kind === "fixture") return 0;
        if (node.kind === "agent") return 1;
        return 2;
      };
      return rank(a) - rank(b) || String(a.label).localeCompare(String(b.label), "zh-CN");
    });
  }

  for (const roomNode of rooms) {
    const directChildren = sortNodes(
      ((childrenByParent.get(roomNode.id) || [])
        .map((childId) => nodeById.get(childId))
        .filter(Boolean))
    );

    const clusters = directChildren.map((parentNode, clusterIndex) => {
      const descendants = sortNodes(
        ((childrenByParent.get(parentNode.id) || [])
          .map((childId) => nodeById.get(childId))
          .filter(Boolean))
      );
      const bounds = clusterDimensions(parentNode, descendants);
      return {
        parentNode,
        descendants,
        clusterIndex,
        width: bounds.width,
        height: bounds.height,
        columns: bounds.columns,
      };
    });

    clusters.forEach((cluster) => {
      const candidates = roomClusterCandidates(roomNode, cluster.clusterIndex);
      const fallback = candidates[0] || { x: roomNode.x, y: roomNode.y };
      let best = fallback;
      let bestPenalty = Number.POSITIVE_INFINITY;
      for (const candidate of candidates) {
        const probe = {
          x: candidate.x,
          y: candidate.y,
          width: cluster.width,
          height: cluster.height,
        };
        let penalty = 0;
        for (const other of placed) {
          if (rectsOverlap(probe, other, 18)) penalty += 1200;
        }
        penalty += Math.hypot(candidate.x - roomNode.x, candidate.y - roomNode.y) * 0.02;
        if (penalty < bestPenalty) {
          bestPenalty = penalty;
          best = candidate;
          if (penalty === 0) break;
        }
      }

      cluster.parentNode.x = best.x;
      cluster.parentNode.y = best.y;
      placed.push({
        x: best.x,
        y: best.y,
        width: cluster.width,
        height: cluster.height,
        nodeId: cluster.parentNode.id,
      });

      cluster.descendants.forEach((childNode, index) => {
        const angle = Math.atan2(best.y - roomNode.y, best.x - roomNode.x) || Math.PI / 2;
        const offset = objectClusterOffset(index, cluster.descendants.length, angle);
        childNode.x = cluster.parentNode.x + offset.x;
        childNode.y = cluster.parentNode.y + offset.y;
        const size = nodeVisualSize(childNode);
        placed.push({
          x: childNode.x,
          y: childNode.y,
          width: size.width,
          height: size.height,
          nodeId: childNode.id,
        });
      });
    });
  }

  for (const node of view.nodes) {
    if (typeof node.labelX !== "number") node.labelX = node.x;
    if (typeof node.labelY !== "number") node.labelY = node.y;
  }
  resolveNodeOverlaps(view);
  resolveHardNodeCollisions(view);
  placeRoomDoorNodes(view);
  assignLabelsBelow(view);
  resolveLabelOverlaps(view);

  for (const edge of view.edges) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target) continue;
    edge.length = Math.hypot(source.x - target.x, source.y - target.y);
  }

  return view;
}

function normalizeVisiblePositions(view) {
  const nodes = view.nodes || [];
  if (!nodes.length) return view;
  const xs = nodes.map((node) => node.x);
  const ys = nodes.map((node) => node.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(1, maxX - minX);
  const spanY = Math.max(1, maxY - minY);
  const targetWidth = LAYOUT_TUNING.viewFit.targetWidth;
  const targetHeight = LAYOUT_TUNING.viewFit.targetHeight;
  const scale = Math.min(targetWidth / spanX, targetHeight / spanY);
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  for (const node of nodes) {
    node.x = (node.x - centerX) * scale;
    node.y = (node.y - centerY) * scale;
  }
  return view;
}

function buildHierarchyMaps(view) {
  const nodeById = new Map((view?.nodes || []).map((node) => [node.id, node]));
  const childrenByParent = new Map();
  for (const node of view?.nodes || []) {
    if (isRoomDoorNode(node)) continue;
    const parentId = String(node.meta?.parent || node.room_id || "");
    if (!parentId || !nodeById.has(parentId)) continue;
    if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
    childrenByParent.get(parentId).push(node.id);
  }
  return { nodeById, childrenByParent };
}

function localNodeRank(node) {
  if (node.kind === "agent") return 0;
  if (node.kind === "fixture") return 1;
  if (node.kind === "movable") return 2;
  return 3;
}

function estimateContainerSize(node, childCount) {
  const base = node.kind === "room"
    ? { width: 260, height: 220, gapX: 74, gapY: 68, columns: 4 }
    : { width: 110, height: 92, gapX: 56, gapY: 52, columns: 3 };
  const cols = Math.max(1, Math.min(base.columns, Math.ceil(Math.sqrt(Math.max(childCount, 1)))));
  const rows = Math.max(1, Math.ceil(childCount / cols));
  return {
    width: Math.max(base.width, 80 + cols * base.gapX),
    height: Math.max(base.height, 80 + rows * base.gapY),
  };
}

function elkPadding(node) {
  if (node.kind === "room") return "[top=36,left=36,bottom=36,right=36]";
  return "[top=24,left=24,bottom=24,right=24]";
}

async function layoutViewWithElk(rawView) {
  if (!elkInstance) return relayoutView(rawView);
  const view = cloneView(rawView);
  const { nodeById, childrenByParent } = buildHierarchyMaps(view);
  const parentIds = new Set(childrenByParent.keys());
  const roomNodes = (view.nodes || []).filter((node) => node.kind === "room");
  const topLevelOrphans = (view.nodes || []).filter((node) => node.kind !== "room" && !node.meta?.parent && !node.room_id);

  function endpointId(nodeId) {
    return parentIds.has(nodeId) ? `hub::${nodeId}` : nodeId;
  }

  function buildElkEntry(nodeId) {
    const node = nodeById.get(nodeId);
    if (!node) return null;
    const childIds = ((childrenByParent.get(nodeId) || []).filter((childId) => nodeById.has(childId)))
      .sort((a, b) => {
        const left = nodeById.get(a);
        const right = nodeById.get(b);
        return localNodeRank(left) - localNodeRank(right) || String(left.label).localeCompare(String(right.label), "zh-CN");
      });
    const size = nodeVisualSize(node);
    if (!childIds.length) {
      return {
        id: node.id,
        width: size.width + 10,
        height: size.height + 10,
      };
    }
    const estimate = estimateContainerSize(node, childIds.length + 1);
    return {
      id: `cluster::${node.id}`,
      width: estimate.width,
      height: estimate.height,
      layoutOptions: {
        "elk.algorithm": "org.eclipse.elk.box",
        "elk.padding": elkPadding(node),
        "org.eclipse.elk.spacing.nodeNode": node.kind === "room" ? "34" : "24",
      },
      children: [
        {
          id: `hub::${node.id}`,
          width: size.width + (node.kind === "room" ? 28 : 18),
          height: size.height + (node.kind === "room" ? 28 : 18),
        },
        ...childIds.map((childId) => buildElkEntry(childId)).filter(Boolean),
      ],
    };
  }

  const graph = {
    id: `floor::${view.floor_id || "main"}`,
    layoutOptions: {
      "elk.algorithm": "org.eclipse.elk.layered",
      "elk.direction": "RIGHT",
      "elk.edgeRouting": "STRAIGHT",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "org.eclipse.elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "org.eclipse.elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "org.eclipse.elk.spacing.nodeNode": "46",
      "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "90",
      "org.eclipse.elk.padding": "[top=24,left=24,bottom=24,right=24]",
    },
    children: [
      ...roomNodes.map((room) => buildElkEntry(room.id)).filter(Boolean),
      ...topLevelOrphans.map((node) => buildElkEntry(node.id)).filter(Boolean),
    ],
    edges: [],
  };

  const addedEdges = new Set();
  for (const edge of view.edges || []) {
    if (edge.kind === "contains") continue;
    const sourceId = endpointId(edge.source);
    const targetId = endpointId(edge.target);
    if (!sourceId || !targetId || sourceId === targetId) continue;
    const key = `${edge.id || `${sourceId}->${targetId}:${edge.kind}`}`;
    if (addedEdges.has(key)) continue;
    addedEdges.add(key);
    graph.edges.push({
      id: key,
      sources: [sourceId],
      targets: [targetId],
    });
  }

  const layout = await elkInstance.layout(graph);
  const positions = new Map();

  function collect(node, offsetX = 0, offsetY = 0) {
    const absX = offsetX + (node.x || 0);
    const absY = offsetY + (node.y || 0);
    if (node.id?.startsWith("hub::")) {
      positions.set(node.id.slice(5), {
        x: absX + (node.width || 0) / 2,
        y: absY + (node.height || 0) / 2,
      });
    } else if (node.id && !node.id.startsWith("cluster::")) {
      positions.set(node.id, {
        x: absX + (node.width || 0) / 2,
        y: absY + (node.height || 0) / 2,
      });
    }
    for (const child of node.children || []) {
      collect(child, absX, absY);
    }
  }

  collect(layout);
  for (const node of view.nodes) {
    const pos = positions.get(node.id);
    if (pos) {
      node.x = pos.x;
      node.y = pos.y;
    }
  }
  normalizeVisiblePositions(view);
  resolveNodeOverlaps(view);
  resolveHardNodeCollisions(view);
  placeRoomDoorNodes(view);
  assignLabelsBelow(view);
  resolveLabelOverlaps(view);

  return view;
}

function layoutViewWithPhysics(rawView, previousView = null) {
  const view = cloneView(rawView);
  const nodeById = new Map(view.nodes.map((node) => [node.id, node]));
  const prevById = mapNodesById(previousView);
  const lockedIds = fixedStructureNodeIds(view, previousView);
  const { childrenByParent } = buildHierarchyMaps(view);
  const rooms = view.nodes.filter((node) => node.kind === "room");
  const roomPositions = computeRoomLayoutWithDagre(view);
  for (const room of rooms) {
    const prev = prevById.get(room.id);
    const pos = lockedIds.has(room.id) && prev ? { x: prev.x, y: prev.y } : roomPositions.get(room.id);
    if (pos) {
      room.x = pos.x;
      room.y = pos.y;
    }
  }

  const roomNeighbors = new Map();
  for (const room of rooms) {
    roomNeighbors.set(room.id, []);
  }
  for (const edge of view.edges || []) {
    if (edge.kind !== "neighbor") continue;
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target || source.kind !== "room" || target.kind !== "room") continue;
    roomNeighbors.get(source.id)?.push(target);
    roomNeighbors.get(target.id)?.push(source);
  }

  const roomDemandRadius = new Map(
    rooms.map((room) => [room.id, estimateRoomDemandRadius(room, nodeById, childrenByParent)])
  );
  if (!previousView) {
    relaxRoomPositions(rooms, roomNeighbors, roomDemandRadius);
  }

  const allRooms = rooms.map((room) => ({
    id: room.id,
    x: room.x,
    y: room.y,
    radius: roomDemandRadius.get(room.id) || Math.max(roomCollisionSize(room).width, roomCollisionSize(room).height) / 2,
  }));

  for (const roomNode of rooms) {
    const directChildren = sortNodesForLayout(
      ((childrenByParent.get(roomNode.id) || [])
        .map((childId) => nodeById.get(childId))
        .filter(Boolean))
    );
    const slotCount = Math.max(10, directChildren.length * 2);
    const shellInner = LAYOUT_TUNING.roomClusters.shellInner;
    const shellOuter = LAYOUT_TUNING.roomClusters.shellOuter;
    const clusters = directChildren.map((parentNode, clusterIndex) => {
      const descendants = sortNodesForLayout(
        ((childrenByParent.get(parentNode.id) || [])
          .map((childId) => nodeById.get(childId))
          .filter(Boolean))
      );
      const bounds = clusterDimensions(parentNode, descendants);
      const prev = prevById.get(parentNode.id);
      const seed = (
        lockedIds.has(parentNode.id) && prev
          ? { x: prev.x, y: prev.y }
          : prev && samePlacementContext(parentNode, prev)
          ? { x: prev.x, y: prev.y }
          : roomClusterCandidates(roomNode, clusterIndex, slotCount)[0]
      ) || { x: roomNode.x, y: roomNode.y };
      return {
        parentNode,
        descendants,
        clusterIndex,
        width: bounds.width,
        height: bounds.height,
        columns: bounds.columns,
        x: seed.x,
        y: seed.y,
        vx: 0,
        vy: 0,
        frozen: lockedIds.has(parentNode.id),
        anchorAngle: chooseAnchorAngle(roomNode, roomNeighbors.get(roomNode.id) || [], clusterIndex, directChildren.length),
      };
    });
    const clusterById = new Map(clusters.map((cluster) => [cluster.parentNode.id, cluster]));
    const controlPairs = [];
    const seenControlPairs = new Set();
    for (const edge of view.edges || []) {
      if (edge.kind !== "controls") continue;
      const sourceNode = nodeById.get(edge.source);
      const targetNode = nodeById.get(edge.target);
      if (!sourceNode || !targetNode) continue;
      if (sourceNode.room_id !== roomNode.id || targetNode.room_id !== roomNode.id) continue;
      const leftKey = clusterKeyForNodeId(sourceNode.id, childrenByParent);
      const rightKey = clusterKeyForNodeId(targetNode.id, childrenByParent);
      if (!leftKey || !rightKey || leftKey === rightKey) continue;
      const leftCluster = clusterById.get(leftKey);
      const rightCluster = clusterById.get(rightKey);
      if (!leftCluster || !rightCluster) continue;
      const pairKey = [leftCluster.parentNode.id, rightCluster.parentNode.id].sort().join("::");
      if (seenControlPairs.has(pairKey)) continue;
      seenControlPairs.add(pairKey);
      controlPairs.push([leftCluster, rightCluster]);
    }

    for (let iter = 0; iter < LAYOUT_TUNING.roomClusters.iterations; iter += 1) {
      for (const cluster of clusters) {
        if (cluster.frozen) {
          cluster.vx = 0;
          cluster.vy = 0;
          continue;
        }
        let fx = 0;
        let fy = 0;
        const anchorRadius =
          shellInner +
          LAYOUT_TUNING.roomClusters.anchorBaseOffset +
          (cluster.clusterIndex % 3) * LAYOUT_TUNING.roomClusters.anchorBandStep;
        const anchorX = roomNode.x + Math.cos(cluster.anchorAngle) * anchorRadius;
        const anchorY = roomNode.y + Math.sin(cluster.anchorAngle) * anchorRadius;
        fx += (anchorX - cluster.x) * LAYOUT_TUNING.roomClusters.anchorPull;
        fy += (anchorY - cluster.y) * LAYOUT_TUNING.roomClusters.anchorPull;

        const toRoomX = cluster.x - roomNode.x;
        const toRoomY = cluster.y - roomNode.y;
        const distToRoom = Math.hypot(toRoomX, toRoomY) || 1;
        const minFromCenter = shellInner + clusterRadius(cluster) * LAYOUT_TUNING.roomClusters.centerPushFactor;
        if (distToRoom < minFromCenter) {
          const push = (minFromCenter - distToRoom) * LAYOUT_TUNING.roomClusters.centerPushStrength;
          fx += (toRoomX / distToRoom) * push;
          fy += (toRoomY / distToRoom) * push;
        }

        for (const otherRoom of allRooms) {
          if (otherRoom.id === roomNode.id) continue;
          const dx = cluster.x - otherRoom.x;
          const dy = cluster.y - otherRoom.y;
          const dist = Math.hypot(dx, dy) || 1;
          const minDist = otherRoom.radius + clusterRadius(cluster) + LAYOUT_TUNING.roomClusters.roomRepulsionPadding;
          if (dist < minDist) {
            const push = (minDist - dist) * LAYOUT_TUNING.roomClusters.roomRepulsionStrength;
            fx += (dx / dist) * push;
            fy += (dy / dist) * push;
          }
        }

        for (const neighborRoom of roomNeighbors.get(roomNode.id) || []) {
          const corridor = pointSegmentDistance(cluster.x, cluster.y, roomNode.x, roomNode.y, neighborRoom.x, neighborRoom.y);
          const minCorridor = clusterRadius(cluster) + LAYOUT_TUNING.roomClusters.corridorPadding;
          if (corridor.distance < minCorridor) {
            const dx = cluster.x - corridor.closestX;
            const dy = cluster.y - corridor.closestY;
            const dist = Math.hypot(dx, dy) || 1;
            const push = (minCorridor - corridor.distance) * LAYOUT_TUNING.roomClusters.corridorRepulsionStrength;
            fx += (dx / dist) * push;
            fy += (dy / dist) * push;
          }
        }

        cluster.vx = (cluster.vx + fx) * LAYOUT_TUNING.roomClusters.damping;
        cluster.vy = (cluster.vy + fy) * LAYOUT_TUNING.roomClusters.damping;
      }

      for (const [left, right] of controlPairs) {
        const dx = right.x - left.x;
        const dy = right.y - left.y;
        const dist = Math.hypot(dx, dy) || 1;
        const target = clusterRadius(left) + clusterRadius(right) + 18;
        const pull = (dist - target) * LAYOUT_TUNING.roomClusters.controlEdgeAttraction;
        const ux = dx / dist;
        const uy = dy / dist;
        left.vx += ux * pull;
        left.vy += uy * pull;
        right.vx -= ux * pull;
        right.vy -= uy * pull;
      }

      for (const cluster of clusters) {
        for (const [left, right] of controlPairs) {
          if (cluster === left || cluster === right) continue;
          const corridor = pointSegmentDistance(cluster.x, cluster.y, left.x, left.y, right.x, right.y);
          const minCorridor = clusterRadius(cluster) + LAYOUT_TUNING.roomClusters.controlCorridorPadding;
          if (corridor.distance < minCorridor) {
            const dx = cluster.x - corridor.closestX;
            const dy = cluster.y - corridor.closestY;
            const dist = Math.hypot(dx, dy) || 1;
            const push = (minCorridor - corridor.distance) * LAYOUT_TUNING.roomClusters.controlCorridorRepulsionStrength;
            cluster.vx += (dx / dist) * push;
            cluster.vy += (dy / dist) * push;
          }
        }
      }

      for (let i = 0; i < clusters.length; i += 1) {
        for (let j = i + 1; j < clusters.length; j += 1) {
          const left = clusters[i];
          const right = clusters[j];
          const dx = right.x - left.x;
          const dy = right.y - left.y;
          const dist = Math.hypot(dx, dy) || 1;
          const minDist =
            clusterRadius(left) +
            clusterRadius(right) +
            LAYOUT_TUNING.roomClusters.clusterRepulsionPadding;
          if (dist < minDist) {
            const push = (minDist - dist) * LAYOUT_TUNING.roomClusters.clusterRepulsionStrength;
            const ux = dx / dist;
            const uy = dy / dist;
            left.vx -= ux * push;
            left.vy -= uy * push;
            right.vx += ux * push;
            right.vy += uy * push;
          }
        }
      }

      for (const cluster of clusters) {
        if (cluster.frozen) continue;
        cluster.x += cluster.vx;
        cluster.y += cluster.vy;
        clampClusterToShell(cluster, roomNode, shellInner, shellOuter);
      }
    }

    clusters.forEach((cluster) => {
      const prevParent = prevById.get(cluster.parentNode.id);
      if (cluster.frozen && prevParent) {
        cluster.parentNode.x = prevParent.x;
        cluster.parentNode.y = prevParent.y;
      } else {
        cluster.parentNode.x = cluster.x;
        cluster.parentNode.y = cluster.y;
      }
      cluster.descendants.forEach((childNode, index) => {
        const prevChild = prevById.get(childNode.id);
        if (lockedIds.has(childNode.id) && prevChild && samePlacementContext(childNode, prevChild)) {
          childNode.x = prevChild.x;
          childNode.y = prevChild.y;
          return;
        }
        const offset = objectClusterOffset(index, cluster.descendants.length, cluster.anchorAngle);
        childNode.x = cluster.parentNode.x + offset.x;
        childNode.y = cluster.parentNode.y + offset.y;
      });
    });
  }

  normalizeVisiblePositions(view);
  stabilizeWithPreviousLayout(view, previousView, lockedIds);
  resolveNodeOverlaps(view, lockedIds);
  resolveHardNodeCollisions(view, lockedIds);
  resolveMovableObstacleConflicts(view, lockedIds);
  resolveHardNodeCollisions(view, lockedIds);
  placeRoomDoorNodes(view);
  assignLabelsBelow(view);
  resolveLabelOverlaps(view);
  return view;
}

async function buildSceneLayouts(scene) {
  const nextLayouts = {};
  const floorViews = scene?.floor_views || {};
  const sceneId = sceneLayoutStorageId(scene);
  const savedSceneLayouts = sceneId ? readSavedLayoutsStore()[sceneId] || {} : {};
  for (const [floorId, view] of Object.entries(floorViews)) {
    const previousView = state.layoutViews?.[floorId] || null;
    const nextSignature = structureSignature(view);
    const nextNonAgentSignature = nonAgentStructureSignature(view);
    try {
      nextLayouts[floorId] = isFloorplanView(view) ? cloneFloorplanView(view) : layoutViewWithPhysics(view, previousView);
      nextLayouts[floorId].__layoutSignature = nextSignature;
      nextLayouts[floorId].__nonAgentLayoutSignature = nextNonAgentSignature;
    } catch (error) {
      console.error("Physics layout failed for floor", floorId, error);
      nextLayouts[floorId] = isFloorplanView(view) ? cloneFloorplanView(view) : relayoutView(view);
      nextLayouts[floorId].__layoutSignature = nextSignature;
      nextLayouts[floorId].__nonAgentLayoutSignature = nextNonAgentSignature;
    }
    nextLayouts[floorId] = applySavedViewLayout(nextLayouts[floorId], savedSceneLayouts[String(floorId)]);
  }
  state.layoutViews = nextLayouts;
}

function appendSvgElement(group, tagName, attributes) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tagName);
  for (const [key, value] of Object.entries(attributes)) {
    element.setAttribute(key, value);
  }
  group.appendChild(element);
  return element;
}

const ICON_PATHS = {
  furniture: "M5 9h14M7 9v10M17 9v10M7 19h10",
  appliance: "M7 3h10v18H7zM9 6h6M12 10a4 4 0 1 0 0 8a4 4 0 1 0 0-8z",
  control: "M12 7a5 5 0 1 0 0 10a5 5 0 1 0 0-10zM12 10v4",
  container: "M5 7h14v4H5zM5 13h14v4H5zM12 9h0M12 15h0",
  tool: "M9 6l3-2l3 2l-1 3h-4zM8 9h8v11H8z",
  decoration: "M12 4c2 2 3 4 3 6c0 4-3 7-3 10c0-3-3-6-3-10c0-2 1-4 3-6zM8 14c2-1 6-1 8 0",
  consumable: "M9 4h6M10 4v3M8 7h8l-1 12H9L8 7M12 10v6",
  personal_item: "M8 7h8M9 7V5h6v2M7 9h10v10H7zM10 12h4M10 15h4",
  agent: "M12 5a3 3 0 1 0 0 6a3 3 0 1 0 0-6zM7 20c0-3 2-6 5-6s5 3 5 6",
  robot: "M7 8h10v8H7zM9 8V5h6v3M9 12h0M15 12h0M10 16h4M5 11H3M21 11h-2M8 20h8",
};

const SEMANTIC_ICON_CATEGORY = {
  furniture: "furniture",
  sofa: "furniture",
  bed: "furniture",
  table: "furniture",
  coffee_table: "furniture",
  desk: "furniture",
  chair: "furniture",
  seat: "furniture",
  shelf: "furniture",
  counter: "furniture",
  drying_rack: "furniture",
  rack: "furniture",
  appliance: "appliance",
  refrigerator: "appliance",
  fridge: "appliance",
  computer: "appliance",
  printer: "appliance",
  water_dispenser: "appliance",
  hand_sanitizer_dispenser: "appliance",
  medicine_fridge: "appliance",
  dispenser: "appliance",
  drinking_fountain: "appliance",
  washer: "appliance",
  washing_machine: "appliance",
  dishwasher: "appliance",
  microwave: "appliance",
  stove: "appliance",
  sink: "appliance",
  faucet: "appliance",
  toilet: "appliance",
  tv: "appliance",
  display: "appliance",
  room_light: "appliance",
  light: "appliance",
  control: "control",
  button: "control",
  knob: "control",
  door: "control",
  container: "container",
  cabinet: "container",
  drawer: "container",
  wardrobe: "container",
  shoe_rack: "container",
  box: "container",
  trash_bin: "container",
  tool: "tool",
  brush: "tool",
  toilet_brush: "tool",
  cloth: "tool",
  broom: "tool",
  watering_can: "tool",
  toothbrush: "tool",
  syringe: "tool",
  medical_cart: "tool",
  iv_bag: "tool",
  saline_bag: "tool",
  wheelchair: "tool",
  cart: "tool",
  decoration: "decoration",
  plant: "decoration",
  potted_plant: "decoration",
  planter: "decoration",
  flowerpot: "decoration",
  vase: "decoration",
  ornament: "decoration",
  decor: "decoration",
  consumable: "consumable",
  milk: "consumable",
  juice: "consumable",
  vegetable: "consumable",
  fruit: "consumable",
  yogurt: "consumable",
  bowl: "consumable",
  cup: "consumable",
  plate: "consumable",
  clothes: "consumable",
  shoes: "consumable",
  book: "consumable",
  medicine: "consumable",
  pill_bottle: "consumable",
  refrigerated_medicine: "consumable",
  infusion_bag: "consumable",
  stationery: "consumable",
  personal_item: "personal_item",
  personal_belonging: "personal_item",
  medical_form: "personal_item",
  prescription_sheet: "personal_item",
  receipt: "personal_item",
  nurse_uniform: "personal_item",
  doctor_coat: "personal_item",
  key: "personal_item",
  wallet: "personal_item",
  phone: "personal_item",
  bag: "personal_item",
  handbag: "personal_item",
  backpack: "personal_item",
  agent: "agent",
  human: "agent",
  robot: "robot",
};

function iconKeyForSemantic(semantic, nodeType = "") {
  if (semantic === "robot") return "robot";
  if (nodeType === "agent") return "agent";
  return SEMANTIC_ICON_CATEGORY[semantic] || "";
}
function semanticTypeOf(node) {
  return String(node?.meta?.semantic_type || "").toLowerCase();
}

function appendNodeIcon(group, node) {
  if (node.kind === "room") return;
  const semantic = semanticTypeOf(node);
  const key = iconKeyForSemantic(semantic, nodeTypeOf(node));
  const d = key ? ICON_PATHS[key] : null;
  if (!d) return;

  const size = nodeVisualSize(node);
  const scale = node.floorplanCircle
    ? Math.max(0.0045, Math.min(size.width, size.height) / 18)
    : node.layout
    ? node.kind === "agent"
      ? Math.max(0.004, Math.min(size.width, size.height) / 52)
      : Math.max(0.006, Math.min(size.width, size.height) / 28)
    : node.kind === "agent"
    ? 0.7
    : (size.width <= 24 ? 0.75 : 0.85);
  const x = node.x;
  const y = node.y;
  const path = appendSvgElement(group, "path", {
    d,
    class: "node-icon",
    transform: `translate(${x} ${y}) scale(${scale}) translate(-12 -12)`,
  });
  // Ensure the icon draws above the fill but below text.
  group.appendChild(path);
}

function nodeClassName(node, temporalClass = node.temporalClass || "") {
  const nodeType = nodeTypeOf(node);
  return (
    node.kind === "room"
      ? `room-node ${node.is_agent_room ? "agent-room" : ""}`
      : `object-node ${nodeType === "movable_object" ? "movable-node" : ""} ${nodeType === "fixed_object" ? "fixture-node" : ""} ${node.kind === "agent" ? "agent-node" : ""} ${temporalClass || ""}`
  ).trim();
}

function appendNodeGeometry(group, node, className, extraAttrs = {}) {
  const layout = normalizeRectLayout(node.layout);
  const nodeType = nodeTypeOf(node);

  if (layout && node.kind === "room") {
    const floorplanAttrs = {};
    floorplanAttrs.fill = node.is_agent_room ? "#f8d7c0" : "#f1e3d0";
    floorplanAttrs.stroke = node.is_agent_room ? "#c75b21" : "#7c4f2f";
    floorplanAttrs["stroke-width"] = "0.3";
    const rectAttrs = {
      x: String(layout.x),
      y: String(layout.y),
      width: String(layout.w),
      height: String(layout.h),
      class: className,
      ...floorplanAttrs,
      ...extraAttrs,
    };
    return appendSvgElement(group, "rect", rectAttrs);
  }

  if (node.floorplanCircle) {
    const radius = Math.max(0.11, (Number(node.width) || floorplanNodeDiameter(node)) / 2);
    return appendSvgElement(group, "circle", {
      cx: String(node.x),
      cy: String(node.y),
      r: String(radius),
      class: className,
      ...extraAttrs,
    });
  }

  if (node.kind === "room") {
    return appendSvgElement(group, "circle", {
      cx: String(node.x),
      cy: String(node.y),
      r: "34",
      class: className,
      ...extraAttrs,
    });
  }

  if (node.kind === "agent" || nodeType === "agent") {
    const size = 18;
    return appendSvgElement(group, "rect", {
      x: String(node.x - size / 2),
      y: String(node.y - size / 2),
      width: String(size),
      height: String(size),
      transform: `rotate(45 ${node.x} ${node.y})`,
      class: className,
      ...extraAttrs,
    });
  }

  if (nodeType === "movable_object" || node.kind === "movable") {
    const size = 24;
    return appendSvgElement(group, "rect", {
      x: String(node.x - size / 2),
      y: String(node.y - size / 2),
      width: String(size),
      height: String(size),
      rx: "4",
      ry: "4",
      class: className,
      ...extraAttrs,
    });
  }

  return appendSvgElement(group, "circle", {
    cx: String(node.x),
    cy: String(node.y),
    r: "16",
    class: className,
    ...extraAttrs,
  });
}

function nodeBounds(node) {
  const layout = normalizeRectLayout(node.layout);
  if (layout && node.kind === "room") return { x: layout.x, y: layout.y, width: layout.w, height: layout.h };
  if (node.floorplanCircle) {
    const size = Number(node.width) || floorplanNodeDiameter(node);
    return { x: node.x - size / 2, y: node.y - size / 2, width: size, height: size };
  }
  if (node.kind === "room") return { x: node.x - 34, y: node.y - 34, width: 68, height: 68 };
  const size = nodeVisualSize(node);
  return {
    x: node.x - size.width / 2,
    y: node.y - size.height / 2,
    width: size.width,
    height: size.height,
  };
}

function appendNodeActiveOverlay(group, node) {
  if (node.kind === "room" || !node.overlayStateClass || !(node.overlayLevel > 0)) return;
  const bounds = nodeBounds(node);
  const overlayHeight = Math.max(1, bounds.height * clamp(node.overlayLevel, 0, 1));
  const safeId = String(node.id).replace(/[^a-zA-Z0-9_-]/g, "_");
  const clipId = `device-overlay-${safeId}-${state.timeline.currentStep}`;
  const defs = appendSvgElement(group, "defs", {});
  const clipPath = appendSvgElement(defs, "clipPath", { id: clipId });
  appendSvgElement(clipPath, "rect", {
    x: String(bounds.x - 1),
    y: String(bounds.y + bounds.height - overlayHeight - 1),
    width: String(bounds.width + 2),
    height: String(overlayHeight + 2),
  });
  appendNodeGeometry(
    group,
    node,
    `device-overlay ${node.overlayStateClass} ${node.flashOnStart ? "overlay-flash" : ""}`.trim(),
    { "clip-path": `url(#${clipId})` },
  );
}

function appendNodeShape(group, node) {
  appendNodeGeometry(group, node, nodeClassName(node));
  appendNodeActiveOverlay(group, node);
}

function nodeLabelClass(node) {
  if (node.kind === "fixture") return "node-label object-label";
  if (node.kind === "movable") return "node-label tool-label";
  if (node.kind === "agent") return "node-label agent-label";
  return "node-label";
}

function floorplanLabelFontSize(node) {
  if (!(node.layout || node.floorplanCircle)) return null;
  if (node.kind === "room") return "0.32px";
  if (node.kind === "agent") return "0.2px";
  return "0.15px";
}

function nodeLabelY(node) {
  if (typeof node.labelY === "number") return node.labelY;
  return node.y + nodeLabelOffset(node);
}

function renderOrderRank(node) {
  if (node.kind === "room") return 0;
  if (node.kind === "fixture") return 1;
  if (node.kind === "movable") return 2;
  if (isAgentNode(node)) return 3;
  return 4;
}

function appendFloorplanDoorways(layer, view) {
  const seen = new Set();
  for (const node of view.nodes || []) {
    if (node.kind !== "room") continue;
    const layout = normalizeRectLayout(node.layout);
    if (!layout?.doorways?.length) continue;
    for (const doorway of layout.doorways) {
      if (!isFiniteNumber(doorway.x) || !isFiniteNumber(doorway.y) || !isFiniteNumber(doorway.length)) continue;
      const key = [
        Number(doorway.x).toFixed(3),
        Number(doorway.y).toFixed(3),
        Number(doorway.length).toFixed(3),
        String(doorway.orientation || ""),
      ].join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      const horizontal = String(doorway.orientation || "").toLowerCase() === "horizontal";
      const x1 = doorway.x;
      const y1 = doorway.y;
      const x2 = horizontal ? doorway.x + doorway.length : doorway.x;
      const y2 = horizontal ? doorway.y : doorway.y + doorway.length;
      appendSvgElement(layer, "line", {
        x1: String(x1),
        y1: String(y1),
        x2: String(x2),
        y2: String(y2),
        class: "floorplan-doorway",
      });
    }
  }
}

function shouldRenderEdgeInFloorplan(edge) {
  return edge.kind !== "neighbor";
}

function shouldAutoFitView(view) {
  const target = computeViewBoxForView(view);
  if (!target) return false;
  if (state.lastRenderedMode !== (isFloorplanView(view) ? "floorplan" : "graph")) return true;
  if (!isFloorplanView(view)) return false;
  const widthRatio = state.viewBox.width / target.width;
  const heightRatio = state.viewBox.height / target.height;
  const xDiff = Math.abs(state.viewBox.x - target.x);
  const yDiff = Math.abs(state.viewBox.y - target.y);
  return (
    widthRatio > 1.35 ||
    heightRatio > 1.35 ||
    widthRatio < 0.75 ||
    heightRatio < 0.75 ||
    xDiff > target.width * 0.18 ||
    yDiff > target.height * 0.18
  );
}

function graphFlowEdgeStyle(kind) {
  if (kind === "neighbor") return { stroke: "rgba(63, 115, 85, 0.95)", strokeWidth: 3 };
  if (kind === "doorway") return { stroke: "rgba(63, 115, 85, 0.95)", strokeWidth: 3 };
  if (kind === "agent_at") return { stroke: "rgba(199, 91, 33, 0.95)", strokeWidth: 3.2, strokeDasharray: "6 3" };
  if (kind === "near") return { stroke: "rgba(199, 91, 33, 0.9)", strokeWidth: 2.8, strokeDasharray: "5 4" };
  if (kind === "contains") return { stroke: "rgba(181, 105, 33, 0.56)", strokeWidth: 2.2, strokeDasharray: "4 4" };
  if (kind === "ontop") return { stroke: "rgba(52, 117, 191, 0.8)", strokeWidth: 2.4 };
  if (kind === "next_to") return { stroke: "rgba(116, 116, 116, 0.7)", strokeWidth: 1.8 };
  if (kind === "controls") return { stroke: "rgba(152, 78, 163, 0.92)", strokeWidth: 2.2, strokeDasharray: "8 4" };
  if (kind === "transport") return { stroke: "rgba(201, 82, 31, 0.85)", strokeWidth: 3.4 };
  return { stroke: "rgba(120, 120, 120, 0.45)", strokeWidth: 1.5 };
}

function graphFlowNodeKind(node) {
  if (node.kind === "room") return "room";
  if (node.kind === "agent" || nodeTypeOf(node) === "agent") return "agent";
  if (node.kind === "movable" || nodeTypeOf(node) === "movable_object") return "movable";
  return "fixture";
}

function graphFlowNodePayload(node) {
  const bounds = nodeBounds(node);
  const width = Math.max(22, bounds.width);
  const height = Math.max(22, bounds.height);
  const semantic = semanticTypeOf(node);
  const iconKey = iconKeyForSemantic(semantic, nodeTypeOf(node));
  const isPinnedDoor = isRoomDoorNode(node);
  return {
    id: String(node.id),
    type: "graphworld",
    position: {
      x: bounds.x - (width - bounds.width) / 2,
      y: bounds.y - (height - bounds.height) / 2,
    },
    width,
    height,
    selected: state.selectedNodeId === node.id,
    draggable: !isPinnedDoor,
    data: {
      rawNode: node,
      label: node.label,
      labelHidden: !!node.labelHidden,
      kind: graphFlowNodeKind(node),
      temporalClass: node.temporalClass || "",
      iconKey,
      width,
      height,
    },
    style: {
      width: `${width}px`,
      height: `${height}px`,
      background: "transparent",
      border: "none",
      boxShadow: "none",
      padding: 0,
    },
  };
}

function graphFlowEdgePayload(edge, nodeMap, index = 0) {
  return {
    id: `${edge.source}-${edge.target}-${edge.kind}-${index}`,
    source: String(edge.source),
    target: String(edge.target),
    sourceHandle: "source",
    targetHandle: "target",
    type: "graphworld",
    selectable: false,
    focusable: false,
    style: graphFlowEdgeStyle(edge.kind),
  };
}

function shiftViewNode(view, nodeId, dx, dy, childrenMap, visited = new Set()) {
  if (!view || visited.has(nodeId)) return;
  visited.add(nodeId);
  const node = (view.nodes || []).find((item) => item.id === nodeId);
  if (!node) return;
  node.x = Number(node.x || 0) + dx;
  node.y = Number(node.y || 0) + dy;
  if (typeof node.labelX === "number") node.labelX += dx;
  if (typeof node.labelY === "number") node.labelY += dy;
  const layout = normalizeRectLayout(node.layout);
  if (layout) {
    node.layout = {
      ...node.layout,
      x: layout.x + dx,
      y: layout.y + dy,
      doorways: (layout.doorways || []).map((doorway) => ({
        ...doorway,
        x: Number(doorway.x || 0) + dx,
        y: Number(doorway.y || 0) + dy,
      })),
    };
  }
  for (const childId of childrenMap.get(nodeId) || []) {
    shiftViewNode(view, childId, dx, dy, childrenMap, visited);
  }
}

function updateGraphFlowNodePosition(view, nodeId, nextPosition) {
  const node = (view?.nodes || []).find((item) => item.id === nodeId);
  if (!node || !nextPosition) return;
  const bounds = nodeBounds(node);
  const dx = Number(nextPosition.x || 0) - bounds.x;
  const dy = Number(nextPosition.y || 0) - bounds.y;
  if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) return;
  const childrenMap = buildChildrenMap(view);
  shiftViewNode(view, nodeId, dx, dy, childrenMap);
  placeRoomDoorNodes(view);
}

function resetCurrentGraphLayout() {
  state.graphFlowFitNonce = (state.graphFlowFitNonce || 0) + 1;
  try {
    const floorId = state.currentFloorId;
    const rawView = state.currentScene?.floor_views?.[floorId];
    if (!rawView) return;
    const nextSignature = structureSignature(rawView);
    const nextNonAgentSignature = nonAgentStructureSignature(rawView);
    const resetView = isFloorplanView(rawView) ? cloneFloorplanView(rawView) : layoutViewWithPhysics(rawView, null);
    resetView.__layoutSignature = nextSignature;
    resetView.__nonAgentLayoutSignature = nextNonAgentSignature;
    state.layoutViews = {
      ...(state.layoutViews || {}),
      [floorId]: resetView,
    };
    persistFloorLayout(state.currentScene, floorId, resetView);
    draw();
  } catch (error) {
    console.error("Failed to reset graph layout", error);
  }
}

function renderGraphFlowView(view) {
  if (!graphFlowContainer || !window.GraphFlowBridge?.mount) return;
  const visibleNodes = (view.nodes || []).map((node) => applyTemporalProfile(node)).filter((node) => !node.hiddenInFloorplan);
  const visibleIds = new Set(visibleNodes.map((node) => String(node.id)));
  const nodeMap = new Map(visibleNodes.map((node) => [String(node.id), node]));
  const edges = (view.edges || [])
    .filter((edge) => !(isFloorplanView(view) && !shouldRenderEdgeInFloorplan(edge)))
    .filter((edge) => visibleIds.has(String(edge.source)) && visibleIds.has(String(edge.target)))
    .map((edge, index) => graphFlowEdgePayload(edge, nodeMap, index));
  window.GraphFlowBridge.mount(
    graphFlowContainer,
    {
      floorKey: `${state.currentScene?.scene?.id || "scene"}:${state.currentFloorId || "floor"}`,
      fitNonce: state.graphFlowFitNonce || 0,
      nodes: visibleNodes.map(graphFlowNodePayload),
      edges,
    },
    {
      onResetLayout: resetCurrentGraphLayout,
      onNodeClick: (node) => {
        if (!node) return;
        const childList = (buildChildrenMap(view).get(node.id) || []);
        if (isFloorplanView(view) && node.kind !== "room" && childList.length) {
          if (state.expandedNodes.has(node.id)) {
            state.expandedNodes.delete(node.id);
          } else {
            state.expandedNodes.add(node.id);
          }
          state.selectedNodeId = node.id;
          draw();
          return;
        }
        info(node);
      },
      onNodeMouseEnter: (node, event) => {
        if (!node || !event) return;
        showHoverTooltip(node, event.clientX, event.clientY);
      },
      onNodeMouseMove: (node, event) => {
        if (!node || !event) return;
        updateHoverTooltip(node, event.clientX, event.clientY);
      },
      onNodeMouseLeave: () => {
        hideHoverTooltip();
      },
      onNodeDragStop: (nodeId, position) => {
        const floorView = state.layoutViews?.[state.currentFloorId];
        if (!floorView) return;
        const rawNode = (floorView.nodes || []).find((item) => String(item.id) === String(nodeId));
        if (rawNode && isRoomDoorNode(rawNode)) return;
        updateGraphFlowNodePosition(floorView, nodeId, position);
        persistFloorLayout(state.currentScene, state.currentFloorId, floorView);
        draw();
      },
    }
  );
}

function draw() {
  const view = state.layoutViews?.[state.currentFloorId] || relayoutView(state.currentScene.floor_views[state.currentFloorId]);
  if (!view) return;
  if (shouldAutoFitView(view)) {
    state.viewBox = computeViewBoxForView(view);
  }
  renderMetrics();
  applyViewBox();
  floorList.innerHTML = "";
  for (const floor of state.currentScene.floors) {
    const btn = document.createElement("button");
    btn.className = `floor-button ${floor.id === state.currentFloorId ? "active" : ""}`;
    btn.innerHTML = `<div><div>${floor.name}</div><div class="floor-meta">${floor.room_count} ${t().rooms}</div></div><div>${floor.id === state.currentScene.agent.current_floor ? t().robot : ""}</div>`;
    btn.addEventListener("click", () => {
      state.currentFloorId = floor.id;
      state.graphFlowFitNonce = (state.graphFlowFitNonce || 0) + 1;
      const targetView = state.layoutViews?.[floor.id] || state.currentScene.floor_views?.[floor.id];
      state.viewBox = computeViewBoxForView(targetView);
      draw();
    });
    floorList.appendChild(btn);
  }
  sceneTitle.textContent = state.currentScene.scene.name;
  floorTitle.textContent = `${view.floor_name} · ${t().floorOnly}`;
  const localizedAgentRoom = state.currentScene.agent.current_room_label || state.currentScene.agent.current_room || "unknown";
  sceneStats.innerHTML = `<div>${view.node_count} ${t().nodes}</div><div>${view.edge_count} ${t().edges}</div><div>${t().agent}: ${localizedAgentRoom}</div>`;
  renderGraphFlowView(view);
  if (state.selectedNodeId) {
    const selectedRawNode = findNodeAcrossFloors(state.selectedNodeId);
    if (selectedRawNode) {
      renderNodeInfo(applyTemporalProfile(selectedRawNode));
    } else if (state.selectedNodeSnapshot) {
      renderNodeInfo(state.selectedNodeSnapshot, { preserveSelection: true });
    }
  } else if (!state.selectedNodeSnapshot) {
    renderNodeInfo(null);
  }
  state.lastRenderedMode = isFloorplanView(view) ? "floorplan" : "graph";
}

function zoomAt(clientX, clientY, scaleFactor) {
  const rect = graphSvg.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const px = (clientX - rect.left) / rect.width;
  const py = (clientY - rect.top) / rect.height;
  const vb = state.viewBox;
  const currentView = state.layoutViews?.[state.currentFloorId] || state.currentScene?.floor_views?.[state.currentFloorId] || null;
  const targetViewBox = computeViewBoxForView(currentView);
  const minWidth = isFloorplanView(currentView) ? targetViewBox.width * 0.08 : defaultViewBox.width * 0.28;
  const minHeight = isFloorplanView(currentView) ? targetViewBox.height * 0.08 : defaultViewBox.height * 0.28;
  const maxWidth = isFloorplanView(currentView) ? targetViewBox.width * 8 : defaultViewBox.width * 5;
  const maxHeight = isFloorplanView(currentView) ? targetViewBox.height * 8 : defaultViewBox.height * 5;
  const focusX = vb.x + px * vb.width;
  const focusY = vb.y + py * vb.height;
  const nextWidth = clamp(vb.width * scaleFactor, minWidth, maxWidth);
  const nextHeight = clamp(vb.height * scaleFactor, minHeight, maxHeight);
  state.viewBox = {
    x: focusX - px * nextWidth,
    y: focusY - py * nextHeight,
    width: nextWidth,
    height: nextHeight,
  };
  applyViewBox();
}

function bindCanvasInteractions() {
  const canvasStage = graphSvg.parentElement;

  graphSvg.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const normalizedDelta = clamp(event.deltaY, -120, 120);
      const intensity = Math.abs(normalizedDelta) / 120;
      const direction = normalizedDelta < 0 ? -1 : 1;
      const scaleFactor = direction < 0 ? 1 - intensity * 0.08 : 1 + intensity * 0.08;
      zoomAt(event.clientX, event.clientY, scaleFactor);
    },
    { passive: false }
  );
  graphSvg.addEventListener("dblclick", () => {
    resetViewBoxForCurrentFloor();
  });

  graphSvg.addEventListener("mousedown", (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    state.pan.active = true;
    state.pan.startX = event.clientX;
    state.pan.startY = event.clientY;
    state.pan.origin = { ...state.viewBox };
    state.pan.moved = false;
    canvasStage.classList.add("dragging");
  });

  window.addEventListener("mousemove", (event) => {
    if (!state.pan.active) return;
    event.preventDefault();
    const rect = graphSvg.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dx = event.clientX - state.pan.startX;
    const dy = event.clientY - state.pan.startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      state.pan.moved = true;
    }
    state.viewBox = {
      x: state.pan.origin.x - (dx / rect.width) * state.pan.origin.width,
      y: state.pan.origin.y - (dy / rect.height) * state.pan.origin.height,
      width: state.pan.origin.width,
      height: state.pan.origin.height,
    };
    applyViewBox();
  });

  window.addEventListener("mouseup", () => {
    if (!state.pan.active) return;
    state.pan.active = false;
    canvasStage.classList.remove("dragging");
    if (state.pan.moved) {
      state.suppressClickUntil = Date.now() + 160;
    }
  });
}

async function setTimelineStep(step, redraw = true) {
  const nextStep = clamp(Math.round(Number(step) || 0), 0, state.timeline.maxStep);
  await refreshSceneAtStep(nextStep);
  renderTimeline();
  if (redraw) draw();
}

function playTimeline() {
  if (state.timeline.playing || state.timeline.currentStep >= state.timeline.maxStep) {
    renderTimeline();
    return;
  }
  state.timeline.playing = true;
  const playbackSeq = (state.timeline.playbackSeq || 0) + 1;
  state.timeline.playbackSeq = playbackSeq;
  renderTimeline();
  const tick = () => {
    if (state.timeline.playbackSeq !== playbackSeq) {
      return;
    }
    state.timeline.timer = null;
    if (!state.timeline.playing) {
      renderTimeline();
      return;
    }
    if (state.timeline.currentStep >= state.timeline.maxStep) {
      stopTimelinePlayback();
      renderTimeline();
      return;
    }
    if (state.timeline.pending) {
      state.timeline.timer = window.setTimeout(tick, timelineDelayMs(state.timeline.speed));
      return;
    }
    setTimelineStep(state.timeline.currentStep + 1).catch((error) => {
      console.error(error);
      stopTimelinePlayback();
      renderTimeline();
      return;
    }).finally(() => {
      if (!state.timeline.playing || state.timeline.playbackSeq !== playbackSeq) {
        renderTimeline();
        return;
      }
      state.timeline.timer = window.setTimeout(tick, timelineDelayMs(state.timeline.speed));
    });
  };
  state.timeline.timer = window.setTimeout(tick, timelineDelayMs(state.timeline.speed));
}

async function loadScene(sceneId) {
  stopTimelinePlayback();
  stopReplayPlayback();
  state.human.session = null;
  setUiMode("scene");
  const res = await fetch(`/api/scene/${encodeURIComponent(sceneId)}?lang=${encodeURIComponent(state.lang)}`);
  if (!res.ok) throw new Error(`Failed to load scene ${sceneId}`);
  state.currentScene = await res.json();
  recordMetricSnapshot(state.currentScene);
  state.currentFloorId = state.currentScene.current_floor || state.currentScene.floors?.[0]?.id || null;
  state.graphFlowFitNonce = (state.graphFlowFitNonce || 0) + 1;
  state.timeline = timelineStateFromScene(state.currentScene);
  state.lastRenderedMode = null;
  state.expandedNodes = new Set();
  // Floor ids are reused across scenes (for example, "F1"), so the previous
  // scene's cached layout must be discarded before rebuilding this scene.
  state.layoutViews = {};
  await buildSceneLayouts(state.currentScene);
  state.viewBox = computeViewBoxForView(state.layoutViews?.[state.currentFloorId] || state.currentScene.floor_views?.[state.currentFloorId]);
  if (!state.replay.sourceSceneId) {
    state.replay.sourceSceneId = sceneId;
  }
  renderTimeline();
  draw();
  renderHumanControls();
}

async function loadSceneList() {
  const res = await fetch(`/api/scenes?lang=${encodeURIComponent(state.lang)}`);
  const payload = await res.json();
  state.scenes = payload.scenes || [];
  renderSceneOptions();
  renderExperimentOptions();
}

async function init() {
  refreshStaticText();
  applyModeVisibility();
  renderExperimentOptions();
  bindCanvasInteractions();
  modeScene.addEventListener("click", () => setUiMode("scene"));
  modeReplay.addEventListener("click", () => setUiMode("replay"));
  timelineStart.addEventListener("click", () => playTimeline());
  timelinePause.addEventListener("click", () => {
    stopTimelinePlayback();
    renderTimeline();
  });
  timelineEnd.addEventListener("click", () => {
    stopTimelinePlayback();
    renderTimeline();
  });
  timelineReset.addEventListener("click", () => {
    stopTimelinePlayback();
    setTimelineStep(0).catch(console.error);
  });
  for (const button of timelineSpeedButtons) {
    if (!button) continue;
    button.addEventListener("click", () => {
      const nextSpeed = Number(button.textContent.replace("x", "")) || 1;
      const wasPlaying = state.timeline.playing;
      if (wasPlaying) {
        stopTimelinePlayback();
      }
      state.timeline.speed = nextSpeed;
      renderTimeline();
      if (wasPlaying) {
        playTimeline();
      }
    });
  }
  renderTimeline();
  renderReplaySummaryBar();
  renderReplayStepPanel();
  renderReplayReadout();
  renderHumanControls();
  if (metricsExpandButton) metricsExpandButton.addEventListener("click", () => openMetricsWindow(t().metricsTitle, metricsPanel?.innerHTML || state.metricsWindow.content));
  if (replayAnalysisButton) replayAnalysisButton.addEventListener("click", () => openReplayAnalysis().catch(console.error));
  if (replayRunExperiment) replayRunExperiment.addEventListener("change", () => syncReplayRunPreset());
  if (runConfigToggle) {
    runConfigToggle.addEventListener("click", () => {
      state.human.runConfigExpanded = !state.human.runConfigExpanded;
      timelineRunConfig?.classList.toggle("is-collapsed", !state.human.runConfigExpanded);
      runConfigToggle.textContent = state.human.runConfigExpanded ? t().runConfigCollapse : t().runConfigExpand;
    });
  }
  if (metricsWindowClose) metricsWindowClose.addEventListener("click", () => closeMetricsWindow());
  if (metricsWindowHeader) metricsWindowHeader.addEventListener("mousedown", (event) => beginMetricsWindowDrag(event));
  window.addEventListener("mousemove", moveMetricsWindow);
  window.addEventListener("mouseup", endMetricsWindowDrag);
  langToggle.addEventListener("click", async () => {
    state.lang = state.lang === "cn" ? "en" : "cn";
    localStorage.setItem("graphworld_lang", state.lang);
    refreshStaticText();
    const currentId = state.currentScene?.scene?.id || sceneSelect.value;
    await loadSceneList();
    if (state.currentScene) {
      if (state.replay.current) {
        await setReplayStep(state.replay.stepIndex);
      } else {
        await loadScene(currentId);
      }
    } else {
      info(null);
    }
  });
  await loadSceneList();
  await loadModelOptions();
  await loadReplayList().catch((error) => {
    console.error(error);
    replaySummaryBar.textContent = error.message;
  });
  replayRunButton.addEventListener("click", () => runReplay().catch((error) => {
    console.error(error);
    replaySummaryBar.textContent = error.message;
  }));
  if (humanEndButton) humanEndButton.addEventListener("click", () => endHumanSession().catch(console.error));
  replayFirst.addEventListener("click", () => setReplayStep(0).catch(console.error));
  replayPrev.addEventListener("click", () => setReplayStep(state.replay.stepIndex - 1).catch(console.error));
  replayNext.addEventListener("click", () => setReplayStep(state.replay.stepIndex + 1).catch(console.error));
  replayLast.addEventListener("click", () => {
    const lastIndex = Math.max(0, (state.replay.current?.run?.steps?.length || 1) - 1);
    setReplayStep(lastIndex).catch(console.error);
  });
  replayPlay.addEventListener("click", () => playReplay());
  replayPause.addEventListener("click", () => stopReplayPlayback());
  replaySlider.addEventListener("input", () => {
    stopReplayPlayback();
    setReplayStep(Number(replaySlider.value) || 0).catch(console.error);
  });
  sceneSelect.addEventListener("change", () => loadScene(sceneSelect.value).catch(console.error));
  if (replayRunScene) {
    replayRunScene.addEventListener("change", () => {
      const nextSceneId = replayRunScene.value;
      if (sceneSelect) sceneSelect.value = nextSceneId;
      if (state.uiMode !== "replay") {
        loadScene(nextSceneId).catch(console.error);
      }
    });
  }
  if (!state.scenes.length) {
    sceneTitle.textContent = t().noScenesTitle;
    floorTitle.textContent = t().noScenesSubtitle;
    return;
  }
  const preferredScene = state.scenes.find((scene) => scene.id === "simple_home_1f") || state.scenes[0];
  sceneSelect.value = preferredScene.id;
  await loadScene(preferredScene.id);
}

init().catch((error) => {
  console.error(error);
  sceneTitle.textContent = t().bootFailTitle;
  floorTitle.textContent = error.message;
});
