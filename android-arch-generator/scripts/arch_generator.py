#!/usr/bin/env python3
"""Android 架构模式代码生成器 — 生成 MVVM/MVI/Clean Architecture 骨架代码"""

import argparse
import os
import sys
from pathlib import Path

# ─── 模板定义 ────────────────────────────────────────────────────────────

PATTERNS_INFO = {
    "mvvm": {
        "name": "MVVM (Model-View-ViewModel)",
        "description": "最常用的 Android 架构模式，ViewModel 持有 UI 状态，View 观察状态变化。",
        "components": ["Fragment (View)", "ViewModel", "Repository", "UiState (Model)", "DI Module"],
        "best_for": "中小型项目、常规 CRUD 页面、快速开发",
    },
    "mvi": {
        "name": "MVI (Model-View-Intent)",
        "description": "单向数据流架构，所有状态变化通过 Intent → Reducer → State 流转。",
        "components": ["Fragment (View)", "ViewModel (Reducer)", "Intent", "State", "SideEffect", "Repository", "DI Module"],
        "best_for": "复杂交互页面、多状态管理、需要状态回放/调试的场景",
    },
    "clean": {
        "name": "Clean Architecture",
        "description": "分层架构，严格的依赖方向（外层依赖内层），通过 UseCase 解耦业务逻辑。",
        "components": ["Fragment (View)", "ViewModel", "UseCase", "Repository", "Entity", "DI Module"],
        "best_for": "大型项目、多人协作、长期维护、需要高测试覆盖率",
    },
}


def _pkg_to_path(package: str) -> str:
    return package.replace(".", "/")


# ─── MVVM 模板 ───────────────────────────────────────────────────────────

def gen_mvvm(name: str, package: str, flow: str, di: str) -> dict:
    """生成 MVVM 架构代码"""
    files = {}
    n = name  # PascalCase feature name
    nl = name[0].lower() + name[1:]  # camelCase

    state_import = ""
    state_type = ""
    state_field = ""
    state_observe = ""

    if flow == "stateflow":
        state_import = "import kotlinx.coroutines.flow.MutableStateFlow\nimport kotlinx.coroutines.flow.StateFlow\nimport kotlinx.coroutines.flow.asStateFlow"
        state_type = f"StateFlow<{n}UiState>"
        state_field = f"""    private val _uiState = MutableStateFlow({n}UiState())
    val uiState: {state_type} = _uiState.asStateFlow()"""
        state_observe = f"""        viewLifecycleOwner.lifecycleScope.launch {{
            viewModel.uiState.collect {{ state ->
                render(state)
            }}
        }}"""
    else:
        state_import = "import androidx.lifecycle.LiveData\nimport androidx.lifecycle.MutableLiveData"
        state_type = f"LiveData<{n}UiState>"
        state_field = f"""    private val _uiState = MutableLiveData({n}UiState())
    val uiState: {state_type} = _uiState"""
        state_observe = f"""        viewModel.uiState.observe(viewLifecycleOwner) {{ state ->
            render(state)
        }}"""

    # UiState
    files[f"data/model/{n}UiState.kt"] = f"""\
package {package}.data.model

data class {n}UiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    // TODO: 添加页面状态字段
)
"""

    # Repository
    files[f"data/{n}Repository.kt"] = f"""\
package {package}.data

import {package}.data.model.{n}UiState
import javax.inject.Inject

class {n}Repository @Inject constructor(
    // TODO: 注入数据源 (API service, DAO, etc.)
) {{
    suspend fun loadData(): Result<{n}UiState> {{
        return try {{
            // TODO: 实现数据加载逻辑
            Result.success({n}UiState())
        }} catch (e: Exception) {{
            Result.failure(e)
        }}
    }}
}}
"""

    # ViewModel
    files[f"ui/{n}ViewModel.kt"] = f"""\
package {package}.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import {package}.data.{n}Repository
import {package}.data.model.{n}UiState
{state_import}
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class {n}ViewModel @Inject constructor(
    private val repository: {n}Repository,
) : ViewModel() {{

{state_field}

    init {{
        loadData()
    }}

    fun loadData() {{
        viewModelScope.launch {{
            // TODO: 设置 loading 状态
            repository.loadData()
                .onSuccess {{ data ->
                    // TODO: 更新 UI 状态
                }}
                .onFailure {{ error ->
                    // TODO: 处理错误
                }}
        }}
    }}
}}
"""

    # Fragment
    files[f"ui/{n}Fragment.kt"] = f"""\
package {package}.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import {package}.data.model.{n}UiState
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class {n}Fragment : Fragment() {{

    private val viewModel: {n}ViewModel by viewModels()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View? {{
        // TODO: 使用 ViewBinding
        // return binding.root
        return super.onCreateView(inflater, container, savedInstanceState)
    }}

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {{
        super.onViewCreated(view, savedInstanceState)
        observeState()
    }}

    private fun observeState() {{
{state_observe}
    }}

    private fun render(state: {n}UiState) {{
        // TODO: 根据状态更新 UI
    }}
}}
"""

    # DI Module
    if di == "hilt":
        files[f"di/{n}Module.kt"] = f"""\
package {package}.di

import {package}.data.{n}Repository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.components.ViewModelComponent

@Module
@InstallIn(ViewModelComponent::class)
object {n}Module {{

    @Provides
    fun provide{n}Repository(): {n}Repository {{
        return {n}Repository()
    }}
}}
"""
    elif di == "koin":
        files[f"di/{n}Module.kt"] = f"""\
package {package}.di

import {package}.data.{n}Repository
import {package}.ui.{n}ViewModel
import org.koin.androidx.viewmodel.dsl.viewModel
import org.koin.dsl.module

val {nl}Module = module {{
    single {{ {n}Repository() }}
    viewModel {{ {n}ViewModel(get()) }}
}}
"""

    return files


# ─── MVI 模板 ────────────────────────────────────────────────────────────

def gen_mvi(name: str, package: str, di: str) -> dict:
    files = {}
    n = name

    # Intent
    files[f"mvi/{n}Intent.kt"] = f"""\
package {package}.mvi

sealed class {n}Intent {{
    object LoadData : {n}Intent()
    object Refresh : {n}Intent()
    // TODO: 添加用户操作意图
}}
"""

    # State
    files[f"mvi/{n}State.kt"] = f"""\
package {package}.mvi

data class {n}State(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    // TODO: 添加页面状态字段
) {{
    companion object {{
        fun initial() = {n}State()
    }}
}}
"""

    # SideEffect
    files[f"mvi/{n}SideEffect.kt"] = f"""\
package {package}.mvi

sealed class {n}SideEffect {{
    data class ShowToast(val message: String) : {n}SideEffect()
    object NavigateBack : {n}SideEffect()
    // TODO: 添加副作用（一次性事件）
}}
"""

    # Repository
    files[f"data/{n}Repository.kt"] = f"""\
package {package}.data

import javax.inject.Inject

class {n}Repository @Inject constructor() {{
    suspend fun loadData(): Result<Unit> {{
        return try {{
            // TODO: 实现数据加载
            Result.success(Unit)
        }} catch (e: Exception) {{
            Result.failure(e)
        }}
    }}
}}
"""

    # ViewModel
    files[f"ui/{n}ViewModel.kt"] = f"""\
package {package}.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import {package}.data.{n}Repository
import {package}.mvi.{n}Intent
import {package}.mvi.{n}SideEffect
import {package}.mvi.{n}State
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class {n}ViewModel @Inject constructor(
    private val repository: {n}Repository,
) : ViewModel() {{

    private val _state = MutableStateFlow({n}State.initial())
    val state: StateFlow<{n}State> = _state.asStateFlow()

    private val _sideEffect = Channel<{n}SideEffect>(Channel.BUFFERED)
    val sideEffect = _sideEffect.receiveAsFlow()

    fun dispatch(intent: {n}Intent) {{
        viewModelScope.launch {{
            reduce(intent)
        }}
    }}

    private suspend fun reduce(intent: {n}Intent) {{
        when (intent) {{
            is {n}Intent.LoadData -> {{
                _state.value = _state.value.copy(isLoading = true)
                repository.loadData()
                    .onSuccess {{
                        _state.value = _state.value.copy(isLoading = false)
                    }}
                    .onFailure {{ error ->
                        _state.value = _state.value.copy(
                            isLoading = false,
                            errorMessage = error.message,
                        )
                        _sideEffect.send({n}SideEffect.ShowToast(error.message ?: "未知错误"))
                    }}
            }}
            is {n}Intent.Refresh -> dispatch({n}Intent.LoadData)
        }}
    }}
}}
"""

    # Fragment
    files[f"ui/{n}Fragment.kt"] = f"""\
package {package}.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import {package}.mvi.{n}Intent
import {package}.mvi.{n}SideEffect
import {package}.mvi.{n}State
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class {n}Fragment : Fragment() {{

    private val viewModel: {n}ViewModel by viewModels()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View? {{
        // TODO: 使用 ViewBinding
        return super.onCreateView(inflater, container, savedInstanceState)
    }}

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {{
        super.onViewCreated(view, savedInstanceState)

        viewLifecycleOwner.lifecycleScope.launch {{
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {{
                launch {{ viewModel.state.collect(::render) }}
                launch {{ viewModel.sideEffect.collect(::handleSideEffect) }}
            }}
        }}

        viewModel.dispatch({n}Intent.LoadData)
    }}

    private fun render(state: {n}State) {{
        // TODO: 根据状态更新 UI
    }}

    private fun handleSideEffect(effect: {n}SideEffect) {{
        when (effect) {{
            is {n}SideEffect.ShowToast -> {{
                Toast.makeText(requireContext(), effect.message, Toast.LENGTH_SHORT).show()
            }}
            is {n}SideEffect.NavigateBack -> {{
                // TODO: 导航返回
            }}
        }}
    }}
}}
"""

    # DI Module
    if di == "hilt":
        files[f"di/{n}Module.kt"] = f"""\
package {package}.di

import {package}.data.{n}Repository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.components.ViewModelComponent

@Module
@InstallIn(ViewModelComponent::class)
object {n}Module {{

    @Provides
    fun provide{n}Repository(): {n}Repository {{
        return {n}Repository()
    }}
}}
"""

    return files


# ─── Clean Architecture 模板 ─────────────────────────────────────────────

def gen_clean(name: str, package: str, di: str) -> dict:
    files = {}
    n = name
    nl = name[0].lower() + name[1:]

    # Domain - Entity
    files[f"domain/model/{n}Entity.kt"] = f"""\
package {package}.domain.model

data class {n}Entity(
    val id: String = "",
    // TODO: 定义领域实体字段
)
"""

    # Domain - Repository Interface
    files[f"domain/repository/{n}RepositoryContract.kt"] = f"""\
package {package}.domain.repository

import {package}.domain.model.{n}Entity

interface {n}RepositoryContract {{
    suspend fun getById(id: String): Result<{n}Entity>
    suspend fun getAll(): Result<List<{n}Entity>>
    suspend fun save(entity: {n}Entity): Result<Unit>
    suspend fun delete(id: String): Result<Unit>
}}
"""

    # Domain - UseCase
    files[f"domain/usecase/Get{n}UseCase.kt"] = f"""\
package {package}.domain.usecase

import {package}.domain.model.{n}Entity
import {package}.domain.repository.{n}RepositoryContract
import javax.inject.Inject

class Get{n}UseCase @Inject constructor(
    private val repository: {n}RepositoryContract,
) {{
    suspend operator fun invoke(id: String): Result<{n}Entity> {{
        return repository.getById(id)
    }}
}}
"""

    files[f"domain/usecase/GetAll{n}UseCase.kt"] = f"""\
package {package}.domain.usecase

import {package}.domain.model.{n}Entity
import {package}.domain.repository.{n}RepositoryContract
import javax.inject.Inject

class GetAll{n}UseCase @Inject constructor(
    private val repository: {n}RepositoryContract,
) {{
    suspend operator fun invoke(): Result<List<{n}Entity>> {{
        return repository.getAll()
    }}
}}
"""

    # Data - Repository Implementation
    files[f"data/repository/{n}Repository.kt"] = f"""\
package {package}.data.repository

import {package}.domain.model.{n}Entity
import {package}.domain.repository.{n}RepositoryContract
import javax.inject.Inject

class {n}Repository @Inject constructor(
    // TODO: 注入数据源 (ApiService, Dao, etc.)
) : {n}RepositoryContract {{

    override suspend fun getById(id: String): Result<{n}Entity> {{
        return try {{
            // TODO: 实现
            Result.success({n}Entity(id = id))
        }} catch (e: Exception) {{
            Result.failure(e)
        }}
    }}

    override suspend fun getAll(): Result<List<{n}Entity>> {{
        return try {{
            // TODO: 实现
            Result.success(emptyList())
        }} catch (e: Exception) {{
            Result.failure(e)
        }}
    }}

    override suspend fun save(entity: {n}Entity): Result<Unit> {{
        return try {{
            // TODO: 实现
            Result.success(Unit)
        }} catch (e: Exception) {{
            Result.failure(e)
        }}
    }}

    override suspend fun delete(id: String): Result<Unit> {{
        return try {{
            // TODO: 实现
            Result.success(Unit)
        }} catch (e: Exception) {{
            Result.failure(e)
        }}
    }}
}}
"""

    # Presentation - UiState
    files[f"presentation/model/{n}UiState.kt"] = f"""\
package {package}.presentation.model

data class {n}UiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    // TODO: 添加 UI 状态
)
"""

    # Presentation - ViewModel
    files[f"presentation/{n}ViewModel.kt"] = f"""\
package {package}.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import {package}.domain.usecase.Get{n}UseCase
import {package}.domain.usecase.GetAll{n}UseCase
import {package}.presentation.model.{n}UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class {n}ViewModel @Inject constructor(
    private val get{n}UseCase: Get{n}UseCase,
    private val getAll{n}UseCase: GetAll{n}UseCase,
) : ViewModel() {{

    private val _uiState = MutableStateFlow({n}UiState())
    val uiState: StateFlow<{n}UiState> = _uiState.asStateFlow()

    fun loadAll() {{
        viewModelScope.launch {{
            _uiState.value = _uiState.value.copy(isLoading = true)
            getAll{n}UseCase()
                .onSuccess {{
                    _uiState.value = _uiState.value.copy(isLoading = false)
                }}
                .onFailure {{ error ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = error.message,
                    )
                }}
        }}
    }}
}}
"""

    # Presentation - Fragment
    files[f"presentation/{n}Fragment.kt"] = f"""\
package {package}.presentation

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import {package}.presentation.model.{n}UiState
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class {n}Fragment : Fragment() {{

    private val viewModel: {n}ViewModel by viewModels()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View? {{
        // TODO: 使用 ViewBinding
        return super.onCreateView(inflater, container, savedInstanceState)
    }}

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {{
        super.onViewCreated(view, savedInstanceState)

        viewLifecycleOwner.lifecycleScope.launch {{
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {{
                viewModel.uiState.collect(::render)
            }}
        }}

        viewModel.loadAll()
    }}

    private fun render(state: {n}UiState) {{
        // TODO: 根据状态更新 UI
    }}
}}
"""

    # DI Module
    if di == "hilt":
        files[f"di/{n}Module.kt"] = f"""\
package {package}.di

import {package}.data.repository.{n}Repository
import {package}.domain.repository.{n}RepositoryContract
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.android.components.ViewModelComponent

@Module
@InstallIn(ViewModelComponent::class)
abstract class {n}Module {{

    @Binds
    abstract fun bind{n}Repository(
        impl: {n}Repository,
    ): {n}RepositoryContract
}}
"""

    return files


# ─── 文件写入 ────────────────────────────────────────────────────────────

def write_files(files: dict, output_dir: str, package: str):
    """写入生成的文件"""
    base = Path(output_dir)
    count = 0
    for rel_path, content in files.items():
        full_path = base / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        count += 1
        print(f"  ✓ {rel_path}")
    print(f"\n共生成 {count} 个文件，输出目录: {output_dir}")


# ─── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Android 架构模式代码生成器")
    sub = parser.add_subparsers(dest="command", help="子命令")

    gen_p = sub.add_parser("generate", help="生成架构代码")
    gen_p.add_argument("feature_name", help="Feature名称 (PascalCase, 如 Home, UserProfile)")
    gen_p.add_argument("--pattern", default="mvvm", choices=["mvvm", "mvi", "clean"],
                       help="架构模式 (默认 mvvm)")
    gen_p.add_argument("--package", default="com.example.app", help="包名")
    gen_p.add_argument("--output", default="./generated", help="输出目录")
    gen_p.add_argument("--flow", default="livedata", choices=["livedata", "stateflow"],
                       help="数据流方式 (mvvm模式, 默认 livedata)")
    gen_p.add_argument("--di", default="hilt", choices=["hilt", "koin", "none"],
                       help="DI框架 (默认 hilt)")

    sub.add_parser("patterns", help="列出架构模式")

    explain_p = sub.add_parser("explain", help="解释架构模式")
    explain_p.add_argument("pattern", choices=["mvvm", "mvi", "clean"])

    args = parser.parse_args()

    if args.command == "generate":
        name = args.feature_name
        if not name[0].isupper():
            name = name[0].upper() + name[1:]

        print(f"生成 {args.pattern.upper()} 架构: {name}")
        print(f"包名: {args.package}")
        print(f"DI: {args.di}")
        print()

        if args.pattern == "mvvm":
            files = gen_mvvm(name, args.package, args.flow, args.di)
        elif args.pattern == "mvi":
            files = gen_mvi(name, args.package, args.di)
        elif args.pattern == "clean":
            files = gen_clean(name, args.package, args.di)
        else:
            print(f"不支持的模式: {args.pattern}", file=sys.stderr)
            sys.exit(1)

        write_files(files, args.output, args.package)

    elif args.command == "patterns":
        print("支持的架构模式:\n")
        for pid, info in PATTERNS_INFO.items():
            print(f"  {pid:8s}  {info['name']}")
            print(f"            {info['description']}")
            print(f"            适合: {info['best_for']}")
            print(f"            组件: {', '.join(info['components'])}")
            print()

    elif args.command == "explain":
        info = PATTERNS_INFO[args.pattern]
        print(f"═══ {info['name']} ═══\n")
        print(info["description"])
        print(f"\n适合场景: {info['best_for']}")
        print(f"\n核心组件:")
        for c in info["components"]:
            print(f"  • {c}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
