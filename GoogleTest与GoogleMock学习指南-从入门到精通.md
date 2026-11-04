# GoogleTest 与 GoogleMock 学习指南 —— 从入门到精通

**作者**：汪亮（bertonwang）
**邮箱**：<47608843@qq.com>
**版本**：v1.0 ｜ **最后更新**：2026-08-13

> **GoogleTest**（gtest）与 **GoogleMock**（gmock）是 C++ 社区事实上的**单元测试与 Mock 双料标准**，被 LLVM、Chromium、TensorFlow、gRPC、Protobuf、OpenCV 等主流工程广泛采用。
> 自 2018 年起两者已合并到同一个仓库 [google/googletest](https://github.com/google/googletest)，共享构建与命名空间。

---

## 📋 目录

- [GoogleTest 与 GoogleMock 学习指南 —— 从入门到精通](#googletest-与-googlemock-学习指南--从入门到精通)
  - [📋 目录](#-目录)
  - [一、简介与定位](#一简介与定位)
  - [二、快速上手](#二快速上手)
    - [2.1 环境构建（CMake FetchContent）](#21-环境构建cmake-fetchcontent)
    - [2.2 第一个测试](#22-第一个测试)
  - [三、GoogleTest 详解](#三googletest-详解)
    - [3.1 断言体系](#31-断言体系)
    - [3.2 Test Fixture（`TEST_F`）](#32-test-fixturetest_f)
    - [3.3 参数化测试（`TEST_P`）](#33-参数化测试test_p)
    - [3.4 类型化测试（`TYPED_TEST`）](#34-类型化测试typed_test)
    - [3.5 死亡测试](#35-死亡测试)
    - [3.6 全局环境与事件监听](#36-全局环境与事件监听)
  - [四、GoogleMock 详解](#四googlemock-详解)
    - [4.1 Mock 一个接口](#41-mock-一个接口)
    - [4.2 EXPECT\_CALL 语法糖](#42-expect_call-语法糖)
    - [4.3 Matcher 匹配器](#43-matcher-匹配器)
    - [4.4 Action 行为](#44-action-行为)
    - [4.5 严格性等级](#45-严格性等级)
  - [五、工程集成最佳实践](#五工程集成最佳实践)
  - [六、常见坑](#六常见坑)
  - [七、参考资料](#七参考资料)

---

## 一、简介与定位

| 字段 | 内容 |
|------|------|
| 定位 | C++ 单元测试框架 + Mock 框架 |
| 语言 | C++14+（旧版本支持 C++11） |
| 许可证 | BSD 3-Clause |
| 依赖 | 无 |
| 官方地址 | <https://github.com/google/googletest> |
| xUnit 定位 | C++ 领域的 JUnit / pytest 对应物 |

**核心卖点**：

1. **零依赖 + Header/静态库两用**，CMake `FetchContent` 一行即可拉起。
2. **富断言宏体系**：`EXPECT_*` 记录错误后继续、`ASSERT_*` 立即终止，覆盖等值/浮点/字符串/异常/死亡场景。
3. **Fixture / 参数化 / 类型化 / 死亡测试** 四类高级模式覆盖 90% 场景。
4. **gmock 的 EXPECT_CALL DSL** 极为强大，几乎能表达"任意调用序列 + 参数 + 返回 + 副作用"约束。

---

## 二、快速上手

### 2.1 环境构建（CMake FetchContent）

```cmake
cmake_minimum_required(VERSION 3.14)
project(my_tests CXX)
set(CMAKE_CXX_STANDARD 17)

include(FetchContent)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
)
# Windows: 让 gtest 用主项目一样的 CRT
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()
add_executable(my_tests test_main.cpp)
target_link_libraries(my_tests PRIVATE GTest::gtest_main GTest::gmock)

include(GoogleTest)
gtest_discover_tests(my_tests)
```

### 2.2 第一个测试

```cpp
#include <gtest/gtest.h>

int Add(int a, int b) { return a + b; }

TEST(AddSuite, PositiveNumbers) {
    EXPECT_EQ(Add(2, 3), 5);
    EXPECT_EQ(Add(0, 0), 0);
}

TEST(AddSuite, Negatives) {
    ASSERT_EQ(Add(-1, -2), -3);   // 失败立即 return
    EXPECT_GT(Add(-1, 5), 0);
}
```

运行：

```bash
ctest --output-on-failure
# 或直接跑
./my_tests --gtest_filter=AddSuite.*
```

---

## 三、GoogleTest 详解

### 3.1 断言体系

| 类别 | 宏 | 说明 |
|------|----|------|
| 布尔 | `EXPECT_TRUE / FALSE(cond)` | 基本断言 |
| 等值 | `EXPECT_EQ / NE / LT / LE / GT / GE(a, b)` | 数值比较 |
| 字符串 | `EXPECT_STREQ / STRNE / STRCASEEQ(a, b)` | C 字符串专用 |
| 浮点 | `EXPECT_FLOAT_EQ / DOUBLE_EQ`、`EXPECT_NEAR(a, b, eps)` | ULP 或绝对误差 |
| 异常 | `EXPECT_THROW / NO_THROW / ANY_THROW` | 异常断言 |
| 死亡 | `EXPECT_DEATH(stmt, regex)` | 进程崩溃/断言场景 |
| 谓词 | `EXPECT_PRED2(fn, a, b)` | 自定义两参谓词 |

- `EXPECT_*` 失败后**继续**当前 test，累积错误
- `ASSERT_*` 失败立即 `return`（不能跨函数栈，需自行 wrapper）

### 3.2 Test Fixture（`TEST_F`）

```cpp
class DatabaseTest : public ::testing::Test {
protected:
    void SetUp() override    { db_.open(":memory:"); }
    void TearDown() override { db_.close(); }
    Database db_;
};

TEST_F(DatabaseTest, InsertAndQuery) {
    db_.exec("INSERT INTO users(name) VALUES('alice')");
    EXPECT_EQ(db_.count("users"), 1);
}
```

Fixture 生命周期：**每个 TEST_F 独立构造/析构**，即测试互相隔离。

### 3.3 参数化测试（`TEST_P`）

```cpp
class DivideTest : public ::testing::TestWithParam<std::tuple<int,int,int>> {};

TEST_P(DivideTest, Basic) {
    auto [a, b, expect] = GetParam();
    EXPECT_EQ(a / b, expect);
}

INSTANTIATE_TEST_SUITE_P(
    IntegerCases, DivideTest,
    ::testing::Values(
        std::make_tuple(10, 2, 5),
        std::make_tuple(9,  3, 3),
        std::make_tuple(-8, 4, -2)));
```

### 3.4 类型化测试（`TYPED_TEST`）

对多种类型跑同一套测试，常用于**容器/模板类**：

```cpp
template <class T>
class RingBufferTest : public ::testing::Test {};

using MyTypes = ::testing::Types<int, double, std::string>;
TYPED_TEST_SUITE(RingBufferTest, MyTypes);

TYPED_TEST(RingBufferTest, PushPop) {
    RingBuffer<TypeParam> rb(3);
    rb.push(TypeParam{});
    EXPECT_EQ(rb.size(), 1u);
}
```

### 3.5 死亡测试

用于验证"断言失败/程序 abort"这类**期望进程死亡**的场景：

```cpp
TEST(SafetyTest, NullPtrDies) {
    int* p = nullptr;
    EXPECT_DEATH(*p = 1, ".*");  // 正则匹配 stderr
}
```

底层通过 `fork()`（Linux/macOS）或 `spawn`（Windows）在子进程中执行 stmt。

### 3.6 全局环境与事件监听

```cpp
class GlobalEnv : public ::testing::Environment {
    void SetUp() override    { InitLogging(); }
    void TearDown() override { ShutdownLogging(); }
};

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    ::testing::AddGlobalTestEnvironment(new GlobalEnv);
    return RUN_ALL_TESTS();
}
```

`::testing::TestEventListener` 可自定义控制台/XML/JUnit 报告输出。

---

## 四、GoogleMock 详解

### 4.1 Mock 一个接口

```cpp
class INetwork {
public:
    virtual ~INetwork() = default;
    virtual int Send(const std::string& url, std::string_view body) = 0;
    virtual bool IsOnline() const = 0;
};

// 用 MOCK_METHOD 宏声明 mock 类
class MockNetwork : public INetwork {
public:
    MOCK_METHOD(int,  Send,     (const std::string& url, std::string_view body), (override));
    MOCK_METHOD(bool, IsOnline, (), (const, override));
};
```

> ⚠️ **关键前提**：被 Mock 的方法必须是 `virtual`。若接口是模板/非虚，可用 *type erasure* 或 [Trompeloeil](https://github.com/rollbear/trompeloeil) 替代。

### 4.2 EXPECT_CALL 语法糖

```cpp
using ::testing::_;
using ::testing::Return;
using ::testing::AtLeast;

TEST(UploaderTest, RetryOnFailure) {
    MockNetwork net;

    EXPECT_CALL(net, IsOnline())
        .Times(AtLeast(1))
        .WillRepeatedly(Return(true));

    EXPECT_CALL(net, Send("https://api/upload", _))
        .Times(2)
        .WillOnce(Return(500))     // 第一次返回 500
        .WillOnce(Return(200));    // 第二次返回 200

    Uploader up(&net);
    EXPECT_TRUE(up.Upload("hello"));
}
```

链式子句结构：`EXPECT_CALL(mock, method(matcher...)).Times(...).InSequence(...).WillOnce(action).WillRepeatedly(action);`

### 4.3 Matcher 匹配器

| Matcher | 含义 |
|---------|------|
| `_` | 任意值 |
| `Eq(x)` / `Ne(x)` / `Lt(x)` … | 数值/等值比较 |
| `StrEq / HasSubstr / MatchesRegex` | 字符串 |
| `Pointee(m)` | 解引用后再匹配 |
| `Field(&S::x, m)` / `Property(&S::y, m)` | 结构体成员匹配 |
| `ElementsAre(a, b, c)` / `Contains(m)` | 容器匹配 |
| `AllOf(m1, m2)` / `AnyOf(...)` / `Not(m)` | 组合逻辑 |

自定义：`MATCHER_P(IsCloseTo, x, "") { return std::abs(arg - x) < 1e-6; }`

### 4.4 Action 行为

| Action | 含义 |
|--------|------|
| `Return(x)` / `ReturnRef(x)` | 直接返回 |
| `Throw(ex)` | 抛异常 |
| `SetArgPointee<0>(v)` | 通过出参写值 |
| `Invoke(fn)` / `InvokeArgument<0>(...)` | 转发到真实函数或回调 |
| `DoAll(a1, a2, ...)` | 顺序执行多个 action |

### 4.5 严格性等级

| 类型 | 未预期的调用 | 建议 |
|------|------------|------|
| `NiceMock<T>` | 静默忽略 | 只关心少数关键调用 |
| `T`（默认） | 打印警告 | 一般场景 |
| `StrictMock<T>` | 直接失败 | 高保真契约测试 |

```cpp
::testing::StrictMock<MockNetwork> net;   // 未 EXPECT_CALL 的调用即 FAIL
```

---

## 五、工程集成最佳实践

1. **✅ 一测一 assert 焦点**：一个 TEST 只验证一件事，失败信息更精确。
2. **✅ 命名规范**：`TestSuite = 被测类名`，`TestName = 场景_期望结果`（如 `Uploader.RetriesOn500ThenSucceeds`）。
3. **✅ 与 CTest 集成**：`gtest_discover_tests()` 自动把每个 TEST 注册为独立 CTest 用例，支持并行。
4. **✅ CI 输出 JUnit XML**：`--gtest_output=xml:report.xml`，方便 Jenkins/GitLab CI 展示。
5. **✅ 代码覆盖率**：GCC `--coverage` + `lcov` / Clang `-fprofile-instr-generate` + `llvm-cov`。
6. **✅ 依赖注入才好 Mock**：写代码时把外部依赖抽成接口 / 通过构造函数注入，是被 Mock 的前提。
7. **⚠️ 不要 Mock 你没有的类型**：Mock 系统调用/第三方类等应做**一层薄封装**再 Mock。

---

## 六、常见坑

1. **`ASSERT_*` 不会跨函数返回**：辅助函数里失败也只 return 辅助函数本身。用 `ASSERT_NO_FATAL_FAILURE(helper())` 或 `SCOPED_TRACE` 定位。
2. **浮点比较误差**：`EXPECT_EQ(1.0, 0.1+0.2*3+0.1)` 会失败；请用 `EXPECT_DOUBLE_EQ` 或 `EXPECT_NEAR`。
3. **未销毁的 Mock 泄漏 EXPECT_CALL**：Mock 对象析构时才校验 EXPECT_CALL 是否满足；提前退出测试会导致误报，可用 `Mock::VerifyAndClearExpectations(&mock)`。
4. **多线程测试竞态**：gtest 本身线程安全，但断言宏在部分平台需要开 `-DGTEST_HAS_PTHREAD=1`；共享状态请自加同步。
5. **死亡测试性能**：每次都 fork，开销大；把慢死亡测试单独放到 `--gtest_filter` 过滤运行。
6. **命名冲突**：TEST 展开生成同名类；同一 TestSuite 下 TestName 不可重复；跨 Suite 也建议全局唯一以便过滤。

---

## 七、参考资料

- 🔗 官方 Primer：<https://google.github.io/googletest/primer.html>
- 🔗 Advanced Guide：<https://google.github.io/googletest/advanced.html>
- 🔗 gMock Cookbook：<https://google.github.io/googletest/gmock_cook_book.html>
- 🔗 gMock Cheat Sheet：<https://google.github.io/googletest/gmock_cheat_sheet.html>
- 📘 *Modern C++ Programming with Test-Driven Development* —— Jeff Langr

---

> ✨ **备注**：GoogleTest 主线跟随最新 C++ 标准，v1.13+ 起最低要求 C++14。欢迎在 PR 中补充或修正。
