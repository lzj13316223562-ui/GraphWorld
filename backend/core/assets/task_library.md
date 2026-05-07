# Task Library

这个文件记录可复用的家庭维护任务模板。后续可以直接拆成 skill：每个模板只使用标准动作空间，不引入额外动作。

标准动作：

```text
move / pick / place / press / open / close / brush / fold
```

通用原则：

- 先 `move` 到目标房间或目标物附近，再交互。
- 如果目标是容器或设备，先 `open`，完成放入/取出后 `close`。
- 如果目标物脏，优先 `brush`；如果目标物错位，优先 `pick` + `place`。
- 如果本 step 没有合法动作，不生成机器人动作。
- 人类事件只会制造混乱；机器人任务目标是恢复状态分和空间分。

## 洗衣服

目标：

把脏衣服放入洗衣机，启动洗衣机；洗完后把湿衣服转移到晾晒位置，干后折叠并收回衣柜。

触发条件：

- 衣物 `semantic_type=clothes/towel/blanket`
- 衣物 `is_dirty=true` 或不在衣柜/卧室合理位置
- 洗衣机 `semantic_type=washer/washing_machine`

动作序列：

```text
move -> dirty_clothes
pick -> dirty_clothes
move -> washer
open -> washer
place -> dirty_clothes, washer
close -> washer
press -> washer_button
```

洗衣完成后的整理序列：

```text
move -> washer
open -> washer
pick -> clean_wet_clothes
move -> drying_rack
place -> clean_wet_clothes, drying_rack
```

晾干后的收纳序列：

```text
move -> dry_clothes
fold -> dry_clothes
pick -> dry_clothes
move -> wardrobe
open -> wardrobe
place -> dry_clothes, wardrobe
close -> wardrobe
```

成功状态：

- 衣物 `is_dirty=false`
- 衣物 `is_wet=false`
- 衣物 `folded=true`
- 衣物位于 `wardrobe` 或卧室合理收纳点
- 洗衣机 `is_on=false`
- 洗衣机 `is_open=false`

常见阻塞：

- 洗衣机门没打开，无法 `place`
- 洗衣机门没关闭，无法 `press`
- 衣物仍然湿，不能 `fold`
- 机器人已经拿着其他物体，不能 `pick`

## 洗碗

目标：

把脏碗、盘子、杯子放入洗碗机并启动；如果没有洗碗机路径，则直接刷洗脏餐具。

触发条件：

- 餐具 `semantic_type=bowl/plate/cup/mug`
- 餐具 `is_dirty=true`
- 洗碗机 `semantic_type=dishwasher`

洗碗机序列：

```text
move -> dirty_dish
pick -> dirty_dish
move -> dishwasher
open -> dishwasher
place -> dirty_dish, dishwasher
close -> dishwasher
press -> dishwasher_button
```

手动刷洗序列：

```text
move -> dirty_dish
brush -> dirty_dish
pick -> dirty_dish
move -> dish_storage_or_sink_area
place -> dirty_dish, dish_storage_or_sink_area
```

成功状态：

- 餐具 `is_dirty=false`
- 餐具位于洗碗机、橱柜、水槽附近或餐具收纳点
- 洗碗机 `is_on=false`
- 洗碗机 `is_open=false`

常见阻塞：

- 洗碗机门没打开，无法放入餐具
- 洗碗机门没关闭，无法启动
- 餐具和机器人不在同一房间，先 `move`

## 收拾鞋子

目标：

把散落在入口、客厅或其他房间的鞋子收回鞋架。

触发条件：

- 物体 `semantic_type=shoes`
- 鞋子不在 `shoe_rack`
- 鞋子 `scattered=true` 或父节点不是鞋架

动作序列：

```text
move -> misplaced_shoes
pick -> misplaced_shoes
move -> shoe_rack
place -> misplaced_shoes, shoe_rack
```

成功状态：

- 鞋子位于 `shoe_rack`
- 鞋子 `scattered=false`
- 入口路径不被鞋子阻塞

常见阻塞：

- 鞋子在其他房间，先移动到鞋子所在房间
- 鞋架不在同一房间，拿起鞋后再 `move` 到鞋架

## 收拾垃圾

目标：

把散落垃圾放入垃圾桶；如果垃圾桶脏，则刷洗垃圾桶表面。

触发条件：

- 散落物体应被归入 `trash_bin`
- 垃圾桶 `semantic_type=trash_bin`
- 垃圾桶 `is_dirty=true` 或周围存在错位垃圾

动作序列：

```text
move -> trash_item
pick -> trash_item
move -> trash_bin
place -> trash_item, trash_bin
```

清洁垃圾桶序列：

```text
move -> trash_bin
brush -> trash_bin
```

成功状态：

- 垃圾物位于 `trash_bin`
- 垃圾桶 `is_dirty=false`
- 垃圾桶周围没有散落物

常见阻塞：

- 垃圾桶满了时不要继续塞垃圾，优先避免让空间分继续下降
- 目标物不是可移动物体时不能 `pick`

## 收拾书本

目标：

把桌面、沙发、地面上的书放回书架、书桌或卧室指定书本区域。

触发条件：

- 物体 `semantic_type=book`
- 书不在书架、书桌或指定书本区域
- 书位于沙发、地面、床、餐桌等临时位置

动作序列：

```text
move -> misplaced_book
pick -> misplaced_book
move -> bookshelf_or_desk
place -> misplaced_book, bookshelf_or_desk
```

成功状态：

- 书位于书架、书桌或指定书本区域
- 书不在沙发、床、地面、餐桌等临时位置

常见阻塞：

- 书和机器人不同房间，先 `move`
- 机器人已经拿着其他物体，先完成当前 `place`

## 通用收纳模板

目标：

把任何可移动物体放回它的语义归属位置。

触发条件：

- 节点 `node_type=movable_object`
- 当前父节点不是语义归属位置
- 当前关系导致空间分下降

动作序列：

```text
move -> misplaced_object
pick -> misplaced_object
move -> preferred_parent
place -> misplaced_object, preferred_parent
```

成功状态：

- 物体父节点等于语义归属位置
- 物体不再出现在临时表面、地面或错误房间

选择优先级：

- 先处理会阻塞人类事件的物体
- 再处理会明显降低空间分的物体
- 再处理脏物体
- 最后处理普通错位物体
