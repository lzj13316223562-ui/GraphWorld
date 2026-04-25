# TongTest 精读笔记

- 论文：The Tong Test: Evaluating Artificial General Intelligence Through Dynamic Embodied Physical and Social Interactions
- 作者：Yujia Peng, Jiaheng Han, Zhenliang Zhang, Lifeng Fan, Tengyu Liu, Siyuan Qi, Xue Feng, Yuxi Ma, Yizhou Wang, Song-Chun Zhu
- 发表：Engineering, 2024
- 论文链接：https://www.sciencedirect.com/science/article/pii/S209580992300293X
- PDF：https://tengyu.ai/assets/pdf/Engineering_TongTest.pdf

## 1. 这篇文章到底在回答什么问题

这篇文章讨论的不是“怎么提升某个 embodied benchmark 的分数”，而是一个更上位的问题：

**AGI 应该如何被定义，以及应该在什么环境里被评估。**

作者的基本判断很明确：

- 经典 Turing Test 不够
- 静态 benchmark 不够
- 固定任务列表也不够

原因是他们认为 AGI 的“通用性”不是数据泛化，而是**任务泛化**。真正的 AGI 必须能在动态环境里持续面对意外情境，并在物理和社会约束下长期表现良好。论文原文把这种环境概括为 `DEPSI`：

- `Dynamic`
- `Embodied`
- `Physical`
- `Social`
- `Interactions`

论文摘要和引言里都明确提出，AGI 的评估应该 rooted in DEPSI，而不是停留在静态测试集或单一任务上。来源：TongTest PDF 第 1 页摘要与引言。

## 2. 为什么作者认为 Turing Test 和传统 benchmark 不够

### 2.1 Turing Test 的问题

作者直接写了，答案“likely no”。原因不是说语言能力不重要，而是 Turing Test 更接近语言层面的可模仿性，不能代表 agent 在开放世界中的任务泛化能力。

他们区分了：

- AI 的 generality：更像数据泛化
- AGI 的 generality：更像任务泛化

也就是说，AGI 不是在更多题上答得更好，而是能在一个持续变化、充满意外场景的环境中做出合适行为。来源：PDF 第 1 页引言，尤其关于 “The answer is likely no” 和 task generalization 的讨论。

### 2.2 固定任务 benchmark 的问题

论文里一个很强的判断是：

如果 `N` 个任务不构成 general intelligence，那么 `N+1` 个任务也一样不构成。

这句话的意思很重要。作者不是想做一个“更大的 benchmark”，而是认为**题库扩容本身不能解决 AGI 评测问题**。真正需要的是一个能够持续生成任务的环境。来源：PDF 第 2 页 `1.2.1 Infinite tasks`。

### 2.3 只看能力也不够

他们后面在评测设计部分把 TongTest 定义成 `value- and ability-oriented` evaluation，而不是只测 ability。也就是说，agent 不只要“会做”，还要看“为什么做、应不应该做、是不是符合人类价值”。来源：PDF 第 5 页 `3.2 Value- and ability-oriented evaluations`。

## 3. 文章提出的五个 AGI 核心特征

TongTest 把 AGI 的关键特征归纳为五个：

1. `Infinite tasks`
2. `Self-driven task generation`
3. `Value alignment`
4. `Causal understanding`
5. `Embodiment`

这五点其实就是全文的骨架。

### 3.1 Infinite tasks

作者认为 AGI 面对的任务不是一个事先列好的有限集合，而是开放环境中不断涌现出来的无限任务。这里“无限任务”不是字面意义上的所有任务，而是强调：

- 任务不是预先穷举的
- 任务来自环境状态和交互过程
- agent 必须适应未事先定义的场景

这点非常关键，因为它把 benchmark 的重点从“任务列表”转向“任务生成环境”。来源：PDF 第 2 页 `1.2.1 Infinite tasks`。

### 3.2 Self-driven task generation

这篇文章最接近 GraphWorld 的地方之一就在这里。

作者举了几个非常生活化的例子：

- 婴儿在哭，agent 会不会主动处理？
- 地上掉了一张百元钞票，agent 会不会把它当垃圾？
- 小孩要锋利剪刀，agent 会不会盲从？

这些例子要表达的是：

**AGI 不能只在接到明确指令时行动，它还必须知道“下一步该做什么”。**

也就是 agent 要有自驱任务生成能力，而不是永远等待 prompt。来源：PDF 第 2 页 `1.2.2 Self-driven task generation`。

### 3.3 Value alignment

作者把 value 放得非常靠前。他们认为 value 不是奖励函数的小修饰，而是 self-driven behavior 的根本驱动力。

文中明确说，AGI 中的 values 不同于 RL 里基于任务目标的 value function。它覆盖更大的空间，而且**不一定依赖任务本身**。例如 agent 偏好整洁、合作、安全，这些偏好不需要某条外部任务指令才能存在。来源：PDF 第 2 页 `1.2.3 Value alignment`。

这一点对 GraphWorld 的启发很直接：

- 机器人不是只为完成一次任务而行动
- 它也应该为了维持环境整洁、安全、舒适而行动
- 这恰好对应我们现在的长期维护场景和双维评分思路

### 3.4 Causal understanding

作者强调的是：AGI 不只是会分类或答题，而是要理解行为与环境之间的因果链条。

他们后面提出一个关键词：

`value–causality–behavior chain`

也就是说：

- value 决定“什么值得做”
- causality 决定“怎样做会产生什么后果”
- behavior 才是最终表现出来的行动

来源：PDF 第 5 页 `3.2` 附近。

### 3.5 Embodiment

embodiment 在这篇文章里不是简单“有个机器人壳子”，而是：

- agent 要身处环境中
- 要受物理规则和社会规则约束
- 要通过与环境及其他 agent 的互动被评测

来源：PDF 第 2 页 `1.2.5 Embodiment` 与引言部分关于 DEPSI 的讨论。

## 4. TongTest 如何定义任务

这一段是文章里很值得注意、但容易被忽视的部分。

作者把任务定义为：

`T = (S_initial, S_target)`

其中开始和目标都不是单一状态，而是**状态等价类**。原因是开放环境里很难要求每次都从完全一致的具体状态开始和结束。来源：PDF 第 1-2 页 `1.1 The AGI task space within DEPSI`。

这个定义说明作者其实已经意识到：在动态环境里，任务不是 rigid script，而是“从一类可接受起点到一类可接受终点”的状态转移。

这和 GraphWorld 很贴，因为我们也不是在追求单条 rigid demo，而是在关心世界状态如何被长期改变。

## 5. TongTest 的知识表示：parse graph + fluent space

这是这篇文章对我们最有技术启发的一段。

在 `3.1 An infinite task-generation system` 里，作者提出：

- 用 `parse graph` 作为基础知识表示
- 用 `fluent space` 表示图中随时间变化的属性空间

他们说 parse graph 用来解析场景中的：

- spatial relations
- temporal relations
- causal relations

在此基础上，`fluent space` 表示这些图属性的时间变化空间。于是所有场景配置都可以被表示为 DEPSI 环境中的连续空间中的点，而任务则是 fluent space 中两个采样点之间的转移。来源：PDF 第 5 页 `3.1`。

这段对 GraphWorld 非常关键，因为它其实给了我们一个很强的相关工作支撑：

- 图不只是地图
- 图也不只是感知产物
- 图可以是任务生成、状态演化和评测的共同底座

如果用一句话概括：

**TongTest 的图是为了支撑 infinite task generation；GraphWorld 的图则进一步被做成了一个实际运行的 world engine。**

## 6. TongTest 的评测设计：U-V 双系统

在 `3.2 Value- and ability-oriented evaluations` 里，作者把评测拆成 `U–V dual system`：

- `U-system`
  描述 agent 对外部物理或社会规则的理解
- `V-system`
  描述 agent 的内在价值系统

来源：PDF 第 5 页 413-418 行附近。

这部分很重要，因为它说明作者并不满足于“任务成功率”这种单一指标，而是希望同时测：

- ability
- value

他们后面还给出一个五维能力框架：

- vision
- natural language
- cognition and reasoning
- motor skills
- learning

并且给出从 level 1 到 level 5 的 benchmark 结构。来源：PDF 第 7 页 Table 2。

## 7. 这篇文章最强的地方

### 7.1 把 AGI 评测从题库拉回世界

它最强的一点，不是提出了多少具体任务，而是把问题重新摆正了：

AGI 不应该定义为“在很多 benchmark 上都不错”，而应该定义为“在动态、具身、物理和社会交互环境中持续表现良好”。

### 7.2 把 value 拉进评测中心

很多 benchmark 只讨论 agent 会不会做，但 TongTest 明确要求讨论：

- agent 会不会主动做
- 做得对不对
- 行为是否符合人的价值

这点非常适合支撑 GraphWorld 里的 `human score`。

### 7.3 图表示不是点缀，而是任务生成机制的一部分

parse graph + fluent space 这一套，不是把图拿来当 visualization，而是直接和任务生成、状态转移绑定在一起。这一点和 GraphWorld 的 graph-native world representation 很同路。

## 8. 这篇文章的局限

### 8.1 更像 perspective / blueprint，不是 fully realized benchmark

这篇文章非常有启发，但它主要还是一篇 perspective。它给出的是评测哲学和系统蓝图，而不是一个已经完全标准化、可直接跑的 benchmark 套件。

### 8.2 value 的量化仍然比较抽象

它非常强调 values，但在“如何稳定、客观、可复现地量化 value”这件事上，工程落地还比较粗。

### 8.3 离可复现系统还有工程鸿沟

从论文文本看，它已经提到了：

- 服务器
- 数据库
- 图形引擎
- VR/AR
- 任务生成
- 评测面板

但这些更多还是架构级设想。相比之下，GraphWorld 的价值反而在于：它已经把其中一部分落成了可运行系统。

## 9. 对 GraphWorld 最直接的启发

### 9.1 GraphWorld 的评测哲学可以直接借 TongTest 的上位叙事

也就是：

- 我们不是在做新的 episode benchmark
- 我们是在做动态、具身、社会化环境中的持续评测

### 9.2 world score / human score 很适合解释成一种 value + ability 的混合评测

虽然 TongTest 不等于我们当前的评分公式，但它给了我们很强的立意来源：评测不应只看 task success，也要看长期价值后果。

### 9.3 parse graph / fluent space 给 GraphWorld 的“图世界”提供理论近邻

我们完全可以把 GraphWorld 描述成：

- 用 graph-native 状态表示世界
- 用 step-wise 状态演化驱动环境
- 用长期运行和持续评分替代单轮成功率

### 9.4 自驱任务生成和持续维护，是我们最值得强调的连接点

TongTest 里最贴 GraphWorld 的，不是“AGI”这个大词，而是：

**agent 不该一直等指令，而应该在开放环境中自己知道下一步该做什么。**

这正是我们现在持续服务机器人路线的核心。

## 10. 写 related works 时可以直接用的几句话

### 版本一：放在引言/动机

TongTest 提出，AGI 的评测应根植于动态、具身、物理与社会交互环境，而不是静态任务集。GraphWorld 与这一方向一致，但进一步将其落地为一个可运行的 graph-native 长时程世界，用于评估机器人在持续演化环境中的长期行为后果。

### 版本二：放在相关工作

与 TongTest 这类强调 DEPSI、无限任务与价值导向评测的上位框架相比，GraphWorld 更关注可执行系统层面的实现：它以场景图作为世界底座，显式建模状态演化、外生事件和人类活动，并通过长期 world/human 双维评分评估 agent 的持续决策能力。

### 版本三：放在方法定位

TongTest 中的 parse graph 与 fluent space 强调图结构与时变状态在 AGI 评测中的核心作用；GraphWorld 则进一步将这一思想实现为一个持续运行的图世界引擎，使图不仅服务任务表示，也直接承载环境演化、动作闭环与长期评测。

## 11. 我对这篇文章的最终判断

如果只说一句话：

**TongTest 最有价值的不是它已经给出了一个成熟 benchmark，而是它把“AGI 应该在什么样的世界里被评估”这个问题重新定义对了。**

对 GraphWorld 来说，它最重要的意义不是细节借鉴，而是方法论背书：

- 为什么要持续环境
- 为什么要社会交互
- 为什么要多维评分
- 为什么不能只做单轮任务

这篇文章在这些点上，和我们是高度同向的。

