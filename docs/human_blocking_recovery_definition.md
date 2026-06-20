# 人类阻塞恢复率定义草案

这份文档用于把“人类阻塞恢复率”定义清楚，先固定口径，再决定是否需要补日志并重跑。

## 1. 我们到底要测什么

人类阻塞恢复率衡量的不是“环境分数有没有回升”，而是：

> 当某个会直接阻塞人类事件的关键前置条件失效后，机器人是否能在下一个相关人类事件发生前把它恢复回来。

它服务的论文论点是：

> 机器人是否真的在支持人类活动，而不只是清理表面脏乱。

## 2. 正式定义

对每一次**可恢复的人类事件失败**，记作一个 blocking case。

- 分母：所有可恢复的 blocking case 数量
- 分子：其中在下一次相同事件到来前，被机器人恢复且下一次事件成功的 case 数量

指标定义为：

```text
人类阻塞恢复率 =
恢复成功的 blocking case 数
/
全部可恢复 blocking case 数
```

## 3. 一个 case 什么时候成立

一个 blocking case 需要同时满足：

1. `event_log` 中某次 human event 的 `ok = false`
2. 失败原因来自该事件的**可恢复前置条件**
3. 该失败不是“世界本身不可恢复”的偶然情况，而是机器人原则上可以处理的状态/物品问题

恢复成功需要满足：

1. 在下一次相同事件到来前，相关前置条件被恢复
2. 下一次相同事件 `ok = true`
3. 恢复不是纯粹由 NPC 自己重新生成资源造成的，而是能从轨迹中看到机器人介入了相关对象/位置

## 4. 为什么现在还不能直接精确计算

现有日志已经有不少关键字段：

- `replay.json` 中的 `event_log`
- human event 的 `ok / failures`
- step 级 scene snapshot
- 机器人动作与 `active_goals`

但还缺 3 个显式归因字段：

1. `precondition_id`
   - 把 `"No clean clothes available."` 这种自然语言失败原因映射到稳定 ID
2. `blocking_issue_id`
   - 把一次失败和后续恢复过程绑定成同一个 case
3. `recovered_by_robot`
   - 明确标记恢复是否由机器人动作导致，而不是 NPC 自然刷新

所以当前可以先把**事件映射和恢复口径定义清楚**，后续补日志后再精算。

## 5. 场景级事件映射

下面这部分直接基于 `backend/core/assets/npc_library.py` 的事件前置条件整理。

### Home

#### getting_dressed

- 事件：`getting_dressed`
- 前置条件：卧室里有 `clothes`，且 `is_dirty = false`、`is_wet = false`、`folded = true`
- 阻塞问题：
  - 没有干净衣服
  - 衣服未晾干
  - 衣服未折叠/未归位
- 机器人恢复：
  - 完成洗衣流程，或把干净衣服放回卧室可用位置
- 对应任务：
  - `laundry_clothes`
  - `restore_initial_position clothes_* -> wardrobe_bedroom`

#### washing_up_morning / washing_up_night

- 事件：`washing_up_morning`、`washing_up_night`
- 前置条件：浴室里有 `toothbrush`、`toothpaste`、`cup`
- 阻塞问题：
  - 洗漱用品缺失或不在浴室
- 机器人恢复：
  - 把洗漱用品放回浴室

#### leaving_home

- 事件：`leaving_home`
- 前置条件：门口有干净且不湿的 `shoes`
- 阻塞问题：
  - 没鞋
  - 鞋是湿的/脏的
- 机器人恢复：
  - 把可用鞋放回 entrance

### Hospital

#### patient_register

- 事件：`patient_register`
- 前置条件：`medical_form_registration` 在 `counter_registration`
- 阻塞问题：
  - 挂号表单不在柜台
- 机器人恢复：
  - 把表单放回挂号台

#### patient_take_medicine

- 事件：`patient_take_medicine`
- 前置条件：
  - `prescription_sheet` 在 `patient_1`
  - `medicine_box_pharmacy` 在 `pharmacy`
- 阻塞问题：
  - 病人没有处方
  - 药房没有药盒
- 机器人恢复：
  - 归还处方单 / 补回药盒

#### patient_infusion

- 事件：`patient_infusion`
- 前置条件：`refrigerated_medicine_pharmacy` 在 `patient_1`
- 阻塞问题：
  - 输液药没有送到病人
- 机器人恢复：
  - 在事件前把相关药物送到 patient

#### doctor_prescribe

- 事件：`doctor_prescribe`
- 前置条件：`prescription_sheet_clinic_1` 在 `outpatient_clinic_1`
- 阻塞问题：
  - 门诊没有空白处方单
- 机器人恢复：
  - 把处方单归位

#### nurse_deliver_medicine

- 事件：`nurse_deliver_medicine`
- 前置条件：`refrigerated_medicine_pharmacy` 在 `medicine_fridge_pharmacy`
- 阻塞问题：
  - 冷藏药不在药冰箱
- 机器人恢复：
  - 把冷藏药放回正确位置

#### nurse_change_bed_sheet

- 事件：`nurse_change_bed_sheet`
- 前置条件：`clean_sheet_storage` 在 `supply_cabinet_treatment_room`
- 阻塞问题：
  - 没有干净床单
- 机器人恢复：
  - 把干净床单补回 supply cabinet

### Supermarket

#### customer_take_cart

- 事件：`customer_take_cart`
- 前置条件：`cart_entrance` 在 `entrance`
- 阻塞问题：
  - 入口没有购物车
- 机器人恢复：
  - 把购物车放回入口

#### customer_shop_produce

- 事件：`customer_shop_produce`
- 前置条件：`fruit_produce_1` 在 `shelf_produce`
- 阻塞问题：
  - 货架没货
- 机器人恢复：
  - 补货到 produce shelf

#### customer_shop_cold

- 事件：`customer_shop_cold`
- 前置条件：
  - `milk_cold_storage_1` 在 `fridge_cold_storage`
  - `fridge_cold_storage.is_open = false`
- 阻塞问题：
  - 冷柜没货
  - 冷柜没关，导致冷链不可用
- 机器人恢复：
  - 补回冷藏商品
  - 关闭冷柜门

#### cashier_prepare

- 事件：`cashier_prepare`
- 前置条件：`counter_checkout.is_dirty = false`
- 阻塞问题：
  - 收银台过脏
- 机器人恢复：
  - 清洁 checkout counter

#### cashier_scan_items

- 事件：`cashier_scan_items`
- 前置条件：`display_checkout.is_on = true`
- 阻塞问题：
  - 收银显示设备未准备好
- 机器人恢复：
  - 打开相关设备

### Office

#### office_focus_work

- 事件：`office_focus_work`
- 前置条件：`report_open_office` 在 `cabinet_manager_office`
- 阻塞问题：
  - 柜里没有归档报告模板
- 机器人恢复：
  - 把报告归档回 cabinet

#### office_team_meeting

- 事件：`office_team_meeting`
- 前置条件：
  - `report_open_office` 在 `desk_open_office_1`
  - `cup_pantry` 在 `counter_pantry`
- 阻塞问题：
  - 工位没有报告
  - pantry 没有可用杯子
- 机器人恢复：
  - 归位 report
  - 清理并归还 cup

#### office_visitor_help

- 事件：`office_visitor_help`
- 前置条件：`cup_pantry` 在 `counter_pantry`
- 阻塞问题：
  - 没有共享杯子
- 机器人恢复：
  - 把杯子洗净并放回 pantry

### Factory

#### factory_worker_prepare

- 事件：`factory_worker_prepare`
- 前置条件：`safety_gear_entrance` 在 `cabinet_entrance`
- 阻塞问题：
  - 入口柜没有安全装备
- 机器人恢复：
  - 把 PPE 放回入口柜

#### factory_load_parts

- 事件：`factory_load_parts`
- 前置条件：`box_warehouse_1` 在 `shelf_warehouse`
- 阻塞问题：
  - 仓库货架无可用零件箱
- 机器人恢复：
  - 把零件箱归位

#### factory_run_assembly

- 事件：`factory_run_assembly`
- 前置条件：
  - `box_warehouse_1` 在 `machine_assembly_line`
  - `finished_product_assembly` 在 `warehouse`
- 阻塞问题：
  - 装配线没装载零件
  - 上一件成品没入库
- 机器人恢复：
  - 把零件箱放到 assembly line
  - 把成品归回 warehouse

#### factory_quality_check

- 事件：`factory_quality_check`
- 前置条件：
  - `finished_product_assembly` 在 `table_workshop`
  - `quality_record_control` 在 `cabinet_control_room`
- 阻塞问题：
  - 没有待检成品
  - 没有质检记录模板
- 机器人恢复：
  - 把成品放回检查台
  - 把记录模板归档到 control room cabinet

#### factory_maintenance_check

- 事件：`factory_maintenance_check`
- 前置条件：`toolkit_workshop` 在 `cabinet_control_room`
- 阻塞问题：
  - control room 里没有工具包
- 机器人恢复：
  - 归还 toolkit

#### factory_shift_handover

- 事件：`factory_shift_handover`
- 前置条件：`quality_record_control` 在 `cabinet_control_room`
- 阻塞问题：
  - 交接前没有归档质检记录
- 机器人恢复：
  - 把质量记录归位

## 6. 推荐的未来日志字段

如果下一步要把这个指标做成正式主指标，建议在 runtime 里新增：

- `human_event_id`
- `precondition_id`
- `blocking_case_id`
- `blocking_target_ids`
- `recovered_step`
- `recovered_by_robot_action`
- `recovery_deadline_step`

这样后续就能直接从日志精算：

```text
blocking case 出现 -> 机器人是否介入 -> 是否在 deadline 前恢复 -> 下一次事件是否成功
```

## 7. 当前建议

当前论文先用 3 个已落地诊断指标：

- 阶段完成率（代理）
- 局部固着率
- 过早切换次数

同时把这份“阻塞恢复率定义草案”写进实验补充说明。等日志字段补齐后，再决定是否重跑：

- `45` 个 fixed `with_robot`
- 或 `75` 个全量 `with_robot`
