from hypothesis import strategies as st


@st.composite
def tags(draw: st.DrawFn) -> str:
    tag_list = draw(
        st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-", min_size=1, max_size=10),
            min_size=0,
            max_size=5
        )
    )
    if not tag_list:
        return ""
    return " ".join(f"@{tag}" for tag in tag_list) + "\n"


@st.composite
def step(draw: st.DrawFn) -> str:
    keyword = draw(st.sampled_from(["Given", "When", "Then", "And", "But"]))
    content = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-", min_size=1, max_size=30))
    return f"    {keyword} {content}"


@st.composite
def steps(draw: st.DrawFn) -> str:
    step_list = draw(st.lists(step(), min_size=1, max_size=5))
    return "\n".join(step_list)


@st.composite
def scenario(draw: st.DrawFn) -> str:
    tag_str = draw(tags())
    name = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-", min_size=1, max_size=30))
    step_str = draw(steps())
    return f"{tag_str}  Scenario: {name}\n{step_str}"


@st.composite
def feature(draw: st.DrawFn) -> str:
    tag_str = draw(tags())
    name = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-", min_size=1, max_size=30))
    desc = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,-_", min_size=0, max_size=50))
    scenario_strs = draw(st.lists(scenario(), min_size=1, max_size=3))
    return f"{tag_str}Feature: {name}\n{desc}\n" + "\n".join(scenario_strs)
