package monitor

import (
	"fmt"

	"github.com/shirou/gopsutil/v4/process"
)

// ProcessCollector collects CPU and memory usage via gopsutil.
type ProcessCollector struct{}

func (c *ProcessCollector) Name() string { return "process" }

func (c *ProcessCollector) Collect(pid int, _ string) (CollectorResult, error) {
	if pid <= 0 {
		return CollectorResult{}, fmt.Errorf("invalid PID: %d", pid)
	}

	proc, err := process.NewProcess(int32(pid))
	if err != nil {
		return CollectorResult{}, fmt.Errorf("process not found (PID %d): %w", pid, err)
	}

	cpuPercent, err := proc.CPUPercent()
	if err != nil {
		cpuPercent = 0
	}

	memInfo, err := proc.MemoryInfo()
	var memMB float64
	if err == nil && memInfo != nil {
		memMB = float64(memInfo.RSS) / (1024 * 1024)
	}

	return CollectorResult{
		CPUPercent: cpuPercent,
		MemoryMB:   memMB,
	}, nil
}
